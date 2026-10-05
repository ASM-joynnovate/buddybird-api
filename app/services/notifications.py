import logging
from datetime import UTC, datetime, time, timedelta
from itertools import groupby
from uuid import UUID, uuid7
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from firebase_admin import exceptions, messaging
from sqlalchemy import false, func, or_, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import sqs
from app.config import config
from app.db import get_or_404, session_factory, transactional
from app.enums import FileStatusEnum, JudgmentStatusEnum, LocaleEnum, NotificationKindEnum, SessionStatusEnum
from app.errors import (
    FileSizeExceededError,
    InvalidProfilePhotoError,
    NotificationReadFailedError,
    NotificationSaveUnavailableError,
    NotificationSendFailedError,
    PushDeliveryRetryError,
    ResourceNotFoundError,
)
from app.fcm import send_push
from app.models import (
    Announcement,
    Device,
    File,
    I18n,
    Notification,
    Parrot,
    PushDelivery,
    Session,
    SessionSound,
    User,
    UserSetting,
)
from app.s3 import S3StorageClient, s3
from app.schemas.base import I18nDTO, I18nTitleRequest, PageParams, UploadDTO, UploadRequest
from app.schemas.notifications import (
    BackofficeNotificationDTO,
    BackofficeNotificationListParams,
    BroadcastNotificationDTO,
    BroadcastNotificationRequest,
    I18nNotificationBodyRequest,
    NotificationDTO,
    NotificationImageDTO,
    SendNotificationRequest,
)
from app.services.sessions import get_judgment_statuses
from app.services.users import MAX_PHOTO_BYTES, PHOTO_TYPES

logger = logging.getLogger(__name__)

PUSH_ENABLED = func.coalesce(UserSetting.push_notification_enabled, true())
NIGHT_ENABLED = func.coalesce(UserSetting.marketing_night_notification_enabled, false())
KIND_ENABLED = {
    NotificationKindEnum.ANNOUNCEMENT: func.coalesce(UserSetting.announcement_notification_enabled, true()),
    NotificationKindEnum.URGENT: true(),
    NotificationKindEnum.MARKETING: func.coalesce(UserSetting.marketing_notification_enabled, false()),
    NotificationKindEnum.REPORT: func.coalesce(UserSetting.report_notification_enabled, true()),
}


def build_notification_dto(notification: Notification, locale: LocaleEnum, storage: S3StorageClient) -> NotificationDTO:
    image = None

    if notification.image_file is not None:
        image = NotificationImageDTO(url=storage.generate_presigned_url(path=notification.image_file.object_key))

    return NotificationDTO(
        id=notification.id,
        kind=notification.kind,
        title=notification.title_i18n.get_text(locale),
        body=notification.body_i18n.get_text(locale),
        image=image,
        data_id=notification.session_id,
        sent_at=notification.sent_at,
        read_at=notification.read_at,
    )


def build_backoffice_notification_dto(
    notification: Notification, storage: S3StorageClient
) -> BackofficeNotificationDTO:
    image = None

    if notification.image_file is not None:
        image = NotificationImageDTO(url=storage.generate_presigned_url(path=notification.image_file.object_key))

    return BackofficeNotificationDTO(
        id=notification.id,
        user_id=notification.user_id,
        kind=notification.kind,
        data_id=notification.session_id,
        title=I18nDTO(ko_kr=notification.title_i18n.ko_kr, en_us=notification.title_i18n.en_us),
        body=I18nDTO(ko_kr=notification.body_i18n.ko_kr, en_us=notification.body_i18n.en_us),
        image=image,
        sent_at=notification.sent_at,
        read_at=notification.read_at,
    )


def get_zone(timezone: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(timezone or "UTC")
    except ZoneInfoNotFoundError, ValueError:
        return ZoneInfo("UTC")


def get_scheduled_at(*, timezone: str | None, started_at: datetime, local_time: time | None) -> datetime:
    if local_time is None:
        return started_at

    zone = get_zone(timezone)
    scheduled_at = datetime.combine(started_at.astimezone(zone).date(), local_time, tzinfo=zone)

    if scheduled_at < started_at:
        scheduled_at += timedelta(days=1)

    return scheduled_at.astimezone(UTC)


def is_night_time(*, at: datetime, timezone: str | None) -> bool:
    hour = at.astimezone(get_zone(timezone)).hour

    return hour >= 21 or hour < 8


def build_notification_i18n(
    *, kind: NotificationKindEnum, title: I18nTitleRequest, body: I18nNotificationBodyRequest
) -> tuple[I18n, I18n]:
    title_prefix = ""
    body_prefix = ""

    if kind == NotificationKindEnum.MARKETING:
        title_prefix = "(광고) "
        body_prefix = f"(광고) {config.MARKETING_CONTACT}\n"

    return (
        I18n(
            ko_kr=title_prefix + title.ko_kr if title.ko_kr is not None else None,
            en_us=title_prefix + title.en_us,
        ),
        I18n(
            ko_kr=body_prefix + body.ko_kr if body.ko_kr is not None else None,
            en_us=body_prefix + body.en_us,
        ),
    )


async def enqueue_push_deliveries(*delivery_ids: UUID) -> None:
    for delivery_id in delivery_ids:
        try:
            await sqs.send(
                queue_url=config.SQS_NOTIFICATION_QUEUE_URL,
                body={"type": "push.send", "delivery_id": str(delivery_id)},
            )
        except Exception:
            logger.exception("푸시 발송 작업 큐 전달 실패; delivery_id=%s", delivery_id)


async def create_notifications(
    *,
    db: AsyncSession,
    kind: NotificationKindEnum,
    title_i18n: I18n,
    body_i18n: I18n,
    image_file_id: UUID | None,
    user_ids: list[UUID] | None,
    local_time: time | None,
    session_id: UUID | None,
) -> tuple[list[Notification], list[UUID]]:
    image_file = None

    if image_file_id is not None:
        image_file = await get_or_404(db=db, model=File, id=image_file_id)

        if image_file.status != FileStatusEnum.UPLOADED.value:
            raise ResourceNotFoundError

    stmt = (
        select(User.id, PUSH_ENABLED, NIGHT_ENABLED, Device)
        .outerjoin(UserSetting, UserSetting.user_id == User.id)
        .outerjoin(Device, Device.user_id == User.id)
        .where(KIND_ENABLED[kind])
        .order_by(User.id)
    )

    if user_ids is not None:
        stmt = stmt.where(User.id.in_(user_ids))

    rows = (await db.execute(stmt)).all()
    now = datetime.now(UTC)
    default_sent_at = get_scheduled_at(timezone=None, started_at=now, local_time=local_time)
    notifications = []
    deliveries = []

    for (user_id, push_enabled, night_enabled), group in groupby(rows, key=lambda row: row[:3]):
        devices = [row.Device for row in group if row.Device is not None]
        scheduled_ats = [
            get_scheduled_at(timezone=device.timezone, started_at=now, local_time=local_time) for device in devices
        ]
        night_blocked = kind == NotificationKindEnum.MARKETING and not night_enabled
        notification = Notification(
            id=uuid7(),
            user_id=user_id,
            kind=kind.value,
            title_i18n=title_i18n,
            body_i18n=body_i18n,
            image_file=image_file,
            session_id=session_id,
            sent_at=min(scheduled_ats, default=default_sent_at),
            is_deleted=False,
        )

        notifications.append(notification)

        for device, scheduled_at in zip(devices, scheduled_ats, strict=True):
            sendable = (
                push_enabled
                and device.push_token is not None
                and not (night_blocked and is_night_time(at=scheduled_at, timezone=device.timezone))
            )

            if sendable:
                deliveries.append(
                    PushDelivery(
                        id=uuid7(),
                        device_id=device.id,
                        notification_id=notification.id,
                        scheduled_at=scheduled_at,
                        queued_at=now if local_time is None else None,
                    )
                )

    db.add_all(notifications)
    await db.flush()

    db.add_all(deliveries)

    return notifications, [delivery.id for delivery in deliveries if delivery.queued_at is not None]


@transactional(unavailable_error=NotificationSendFailedError)
async def create(
    *, db: AsyncSession, storage: S3StorageClient, user: User, data: SendNotificationRequest
) -> tuple[BackofficeNotificationDTO | None, list[UUID]]:
    title_i18n, body_i18n = build_notification_i18n(kind=data.kind, title=data.title, body=data.body)
    notifications, delivery_ids = await create_notifications(
        db=db,
        kind=data.kind,
        title_i18n=title_i18n,
        body_i18n=body_i18n,
        image_file_id=data.image_file_id,
        user_ids=[user.id],
        local_time=None,
        session_id=None,
    )

    if not notifications:
        return None, []

    return build_backoffice_notification_dto(notifications[0], storage), delivery_ids


async def send(
    *, db: AsyncSession, storage: S3StorageClient, user: User, data: SendNotificationRequest
) -> BackofficeNotificationDTO | None:
    dto, delivery_ids = await create(db=db, storage=storage, user=user, data=data)

    await enqueue_push_deliveries(*delivery_ids)

    return dto


@transactional(unavailable_error=NotificationSendFailedError)
async def create_broadcast(*, db: AsyncSession, data: BroadcastNotificationRequest) -> tuple[int, list[UUID]]:
    title_i18n, body_i18n = build_notification_i18n(kind=data.kind, title=data.title, body=data.body)
    notifications, delivery_ids = await create_notifications(
        db=db,
        kind=data.kind,
        title_i18n=title_i18n,
        body_i18n=body_i18n,
        image_file_id=data.image_file_id,
        user_ids=data.user_ids,
        local_time=data.push_local_time,
        session_id=None,
    )

    return len(notifications), delivery_ids


async def broadcast(*, db: AsyncSession, data: BroadcastNotificationRequest) -> BroadcastNotificationDTO:
    notification_count, delivery_ids = await create_broadcast(db=db, data=data)

    await enqueue_push_deliveries(*delivery_ids)

    return BroadcastNotificationDTO(notification_count=notification_count)


@transactional
async def create_report(*, db: AsyncSession, session_id: UUID) -> list[UUID]:
    session = await db.get(Session, session_id)
    statuses = await get_judgment_statuses(db=db, sessions=[session])

    stmt = (
        select(SessionSound.id)
        .join(File, File.id == SessionSound.audio_file_id)
        .where(SessionSound.session_id == session_id, File.status == FileStatusEnum.UPLOADED.value)
        .limit(1)
    )
    uploaded_sound_id = await db.scalar(stmt)

    stmt = select(Notification.id).where(Notification.session_id == session_id)
    report_id = await db.scalar(stmt)

    if statuses[session_id] != JudgmentStatusEnum.DONE or uploaded_sound_id is None or report_id is not None:
        return []

    stmt = select(Parrot.name).where(Parrot.user_id == session.user_id).order_by(Parrot.created_at)
    names = (await db.scalars(stmt)).all()
    subject_ko = "우리 앵무새가"
    subject_en = "your parrot"

    if len(names) == 1:
        has_final_consonant = "가" <= names[0][-1] <= "힣" and (ord(names[0][-1]) - ord("가")) % 28 != 0
        subject_ko = names[0] + ("이" if has_final_consonant else "가")
        subject_en = names[0]
    elif names:
        others = "other" if len(names) == 2 else "others"
        subject_ko = f"{names[0]} 외 {len(names) - 1}마리가"
        subject_en = f"{names[0]} and {len(names) - 1} {others}"

    _, delivery_ids = await create_notifications(
        db=db,
        kind=NotificationKindEnum.REPORT,
        title_i18n=I18n(ko_kr="학습 리포트가 준비됐어요", en_us="Your learning report is ready"),
        body_i18n=I18n(
            ko_kr=f"앵무새 소리 분석이 끝났어요. {subject_ko} 낸 소리를 들어 보세요!",
            en_us=f"We finished analyzing the sounds. Come listen to what {subject_en} said!",
        ),
        image_file_id=None,
        user_ids=[session.user_id],
        local_time=None,
        session_id=session_id,
    )

    return delivery_ids


async def send_report(*, db: AsyncSession, session_ids: list[UUID]) -> None:
    for session_id in session_ids:
        try:
            delivery_ids = await create_report(db=db, session_id=session_id)

            await enqueue_push_deliveries(*delivery_ids)
        except Exception:
            logger.exception("리포트 알림 생성 실패; session_id=%s", session_id)


@transactional(unavailable_error=NotificationSaveUnavailableError)
async def add_image(*, db: AsyncSession, storage: S3StorageClient, data: UploadRequest) -> UploadDTO:
    if data.content_type not in PHOTO_TYPES:
        raise InvalidProfilePhotoError

    if data.file_size > MAX_PHOTO_BYTES:
        raise FileSizeExceededError

    file_id = uuid7()

    image_file = File(
        id=file_id,
        file_name="image.jpg",
        file_path=f"notification/{file_id}",
        file_size=data.file_size,
        file_type="image/jpeg",
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )

    db.add(image_file)

    await db.flush()

    return storage.generate_presigned_upload(
        file_id=file_id,
        path=f"upload/{image_file.object_key}",
        content_type=data.content_type,
        file_size=data.file_size,
    )


async def get_list(
    *, db: AsyncSession, storage: S3StorageClient, user: User, locale: LocaleEnum, query: PageParams
) -> tuple[list[NotificationDTO], int]:
    stmt = select(Notification).where(Notification.user_id == user.id, Notification.sent_at <= datetime.now(UTC))
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    notifications = (
        await db.scalars(
            stmt.order_by(Notification.sent_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return [build_notification_dto(notification, locale, storage) for notification in notifications], total


async def get_backoffice_list(
    *, db: AsyncSession, storage: S3StorageClient, query: BackofficeNotificationListParams
) -> tuple[list[BackofficeNotificationDTO], int]:
    stmt = select(Notification)

    if query.user_id is not None:
        stmt = stmt.where(Notification.user_id == query.user_id)

    if query.kind is not None:
        stmt = stmt.where(Notification.kind == query.kind.value)

    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    notifications = (
        await db.scalars(
            stmt.order_by(Notification.sent_at.desc(), Notification.id.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return [build_backoffice_notification_dto(notification, storage) for notification in notifications], total


@transactional(unavailable_error=NotificationReadFailedError)
async def mark_read(
    *, db: AsyncSession, storage: S3StorageClient, notification: Notification, locale: LocaleEnum
) -> NotificationDTO:
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)

    await db.flush()

    return build_notification_dto(notification, locale, storage)


@transactional(unavailable_error=NotificationReadFailedError)
async def mark_all_read(*, db: AsyncSession, user: User) -> None:
    now = datetime.now(UTC)

    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None), Notification.sent_at <= now)
        .values(read_at=now)
    )


async def dispatch_due_pushes() -> None:
    now = datetime.now(UTC)

    async with session_factory() as db:
        stmt = select(Announcement).where(
            Announcement.push_enabled,
            Announcement.push_prepared_at.is_(None),
            Announcement.starts_at <= now,
            or_(Announcement.ends_at.is_(None), Announcement.ends_at > now),
        )
        announcements = (await db.scalars(stmt)).all()

        stmt = (
            select(Device)
            .join(User, User.id == Device.user_id)
            .outerjoin(UserSetting, UserSetting.user_id == User.id)
            .where(Device.push_token.is_not(None), PUSH_ENABLED, KIND_ENABLED[NotificationKindEnum.ANNOUNCEMENT])
        )

        for announcement in announcements:
            devices = (await db.scalars(stmt)).all()
            started_at = max(announcement.starts_at, announcement.created_at)
            announcement.push_prepared_at = now

            db.add_all(
                PushDelivery(
                    device_id=device.id,
                    announcement_id=announcement.id,
                    scheduled_at=get_scheduled_at(
                        timezone=device.timezone, started_at=started_at, local_time=announcement.push_local_time
                    ),
                )
                for device in devices
            )

        await db.commit()

        while True:
            stmt = (
                select(PushDelivery)
                .where(PushDelivery.queued_at.is_(None), PushDelivery.scheduled_at <= now)
                .limit(100)
            )
            deliveries = (await db.scalars(stmt)).all()

            if not deliveries:
                return

            for delivery in deliveries:
                delivery.queued_at = now

            await db.commit()
            await enqueue_push_deliveries(*(delivery.id for delivery in deliveries))


async def deliver(delivery_id: UUID) -> None:
    async with session_factory() as db:
        delivery = await db.get(PushDelivery, delivery_id)

        if delivery is None or delivery.processed_at is not None:
            return

        now = datetime.now(UTC)
        expired = False

        if delivery.notification_id is not None:
            notification = await db.get(Notification, delivery.notification_id)
            kind = notification.kind
            title_i18n = notification.title_i18n
            body_i18n = notification.body_i18n
            image_file = notification.image_file
            data = {"kind": kind, "notification_id": str(notification.id), "sent_at": notification.sent_at.isoformat()}

            if notification.session_id is not None:
                data["data_id"] = str(notification.session_id)
        else:
            announcement = await db.get(
                Announcement, delivery.announcement_id, execution_options={"include_deleted": True}
            )
            kind = NotificationKindEnum.ANNOUNCEMENT.value
            title_i18n = announcement.title_i18n
            body_i18n = announcement.body_i18n
            image_file = announcement.images[0].file if announcement.images else None
            data = {"kind": kind, "data_id": str(announcement.id)}
            expired = announcement.is_deleted or (announcement.ends_at is not None and announcement.ends_at <= now)

        stmt = (
            select(Device, NIGHT_ENABLED)
            .join(User, User.id == Device.user_id)
            .outerjoin(UserSetting, UserSetting.user_id == User.id)
            .where(
                Device.id == delivery.device_id,
                Device.push_token.is_not(None),
                Device.id.not_in(
                    select(Session.station_device_id).where(Session.status == SessionStatusEnum.RUNNING.value)
                ),
                PUSH_ENABLED,
                KIND_ENABLED[kind],
            )
        )
        row = (await db.execute(stmt)).first()
        sendable = (
            row is not None
            and not expired
            and not (
                kind == NotificationKindEnum.MARKETING
                and not row[1]
                and is_night_time(at=now, timezone=row.Device.timezone)
            )
        )

        if sendable:
            device = row.Device
            locale = LocaleEnum(device.locale)
            body = body_i18n.get_text(locale) if body_i18n is not None else ""
            image_url = s3.generate_presigned_url(path=image_file.object_key) if image_file is not None else None

            if delivery.announcement_id is not None:
                body = body[:500]

            if kind == NotificationKindEnum.MARKETING and locale == LocaleEnum.KO_KR and body_i18n.ko_kr is not None:
                body += "\n무료 수신거부: 프로필 > 설정 > 알림에서 마케팅 알림 Off"
            elif kind == NotificationKindEnum.MARKETING:
                body += "\nUnsubscribe for free: Profile > Settings > Notifications > turn off Marketing alerts"

            try:
                await send_push(
                    token=device.push_token,
                    title=title_i18n.get_text(locale),
                    body=body,
                    image_url=image_url,
                    data=data,
                )
            except messaging.UnregisteredError, messaging.SenderIdMismatchError:
                device.push_token = None
            except (
                exceptions.UnavailableError,
                exceptions.InternalError,
                exceptions.ResourceExhaustedError,
                exceptions.DeadlineExceededError,
            ) as exc:
                raise PushDeliveryRetryError from exc
            except exceptions.FirebaseError:
                logger.exception("푸시 발송 실패; delivery_id=%s", delivery_id)

        delivery.processed_at = datetime.now(UTC)

        await db.commit()
