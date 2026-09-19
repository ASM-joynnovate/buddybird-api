import logging
from datetime import UTC, date, datetime
from uuid import UUID

from firebase_admin import exceptions, messaging
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import sqs
from app.config import config
from app.db import get_or_404, session_factory, transactional
from app.enums import DeviceRoleEnum, NotificationKindEnum
from app.errors import NotificationReadFailedError, NotificationSendFailedError, PushDeliveryRetryError
from app.fcm import send_push
from app.models import Device, File, Notification, User
from app.s3 import S3StorageClient, get_s3
from app.schemas.base import PageParams
from app.schemas.notifications import NotificationDTO, NotificationImageDTO
from app.services.settings import get_or_create_settings

logger = logging.getLogger(__name__)


def build_notification_dto(notification: Notification, storage: S3StorageClient) -> NotificationDTO:
    image = None

    if notification.image_file is not None:
        image = NotificationImageDTO(url=storage.generate_presigned_url(path=notification.image_file.object_key))

    return NotificationDTO(
        id=notification.id,
        kind=notification.kind,
        title=notification.title,
        body=notification.body,
        image=image,
        sound_id=notification.sound_id,
        emergency_event_id=notification.emergency_event_id,
        report_date=notification.report_date,
        sent_at=notification.sent_at,
        read_at=notification.read_at,
    )


@transactional(unavailable_error=NotificationSendFailedError)
async def create(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    user: User,
    kind: NotificationKindEnum,
    title: str,
    body: str,
    emergency_event_id: UUID | None = None,
    image_file_id: UUID | None = None,
    sound_id: UUID | None = None,
    report_date: date | None = None,
) -> NotificationDTO | None:
    setting = await get_or_create_settings(db=db, user=user)
    enabled = {
        NotificationKindEnum.EMERGENCY: setting.notify_emergency,
        NotificationKindEnum.MIMICRY: setting.notify_mimicry,
        NotificationKindEnum.STATION_DISCONNECT: setting.notify_station_disconnect,
        NotificationKindEnum.DAILY_SUMMARY: setting.notify_daily_summary,
        NotificationKindEnum.STREAK: setting.notify_streak,
    }[kind]

    if not enabled:
        return None

    image_file = None

    if image_file_id is not None:
        image_file = await get_or_404(db=db, model=File, id=image_file_id)

    notification = Notification(
        user_id=user.id,
        kind=kind.value,
        title=title,
        body=body,
        emergency_event_id=emergency_event_id,
        image_file=image_file,
        sound_id=sound_id,
        report_date=report_date,
        sent_at=datetime.now(UTC),
        is_deleted=False,
    )

    db.add(notification)
    await db.flush()

    return build_notification_dto(notification, storage)


async def send(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    user: User,
    kind: NotificationKindEnum,
    title: str,
    body: str,
    emergency_event_id: UUID | None = None,
    image_file_id: UUID | None = None,
    sound_id: UUID | None = None,
    report_date: date | None = None,
) -> NotificationDTO | None:
    dto = await create(
        db=db,
        storage=storage,
        user=user,
        kind=kind,
        title=title,
        body=body,
        emergency_event_id=emergency_event_id,
        image_file_id=image_file_id,
        sound_id=sound_id,
        report_date=report_date,
    )

    if dto is not None:
        try:
            await sqs.send(
                queue_url=config.SQS_NOTIFICATION_QUEUE_URL,
                body={"type": "notification.send", "notification_id": str(dto.id)},
            )
        except Exception:
            logger.warning("알림 발송 작업 큐 전달 실패")

    return dto


async def get_list(
    *, db: AsyncSession, storage: S3StorageClient, user: User, query: PageParams
) -> tuple[list[NotificationDTO], int]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    notifications = (
        await db.scalars(
            stmt.order_by(Notification.sent_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return [build_notification_dto(notification, storage) for notification in notifications], total


@transactional(unavailable_error=NotificationReadFailedError)
async def mark_read(*, db: AsyncSession, storage: S3StorageClient, notification: Notification) -> NotificationDTO:
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)

    await db.flush()

    return build_notification_dto(notification, storage)


@transactional(unavailable_error=NotificationReadFailedError)
async def mark_all_read(*, db: AsyncSession, user: User) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )


async def deliver(notification_id: UUID) -> None:
    async with session_factory() as db:
        notification = await db.get(Notification, notification_id)

        if notification is None:
            logger.warning("알림이 없어 발송을 건너뜀; notification_id=%s", notification_id)
            return

        device = await db.scalar(
            select(Device).where(
                Device.user_id == notification.user_id,
                Device.role == DeviceRoleEnum.VIEWER.value,
                Device.push_token.is_not(None),
            )
        )

        if device is None:
            logger.info("push 토큰이 있는 viewer 기기가 없어 발송을 건너뜀; notification_id=%s", notification_id)
            return

        image_url = None

        if notification.image_file is not None:
            image_url = get_s3().generate_presigned_url(path=notification.image_file.object_key)

        data = {"kind": notification.kind, "notification_id": str(notification.id)}

        if notification.emergency_event_id is not None:
            data["emergency_event_id"] = str(notification.emergency_event_id)

        if notification.sound_id is not None:
            data["sound_id"] = str(notification.sound_id)

        if notification.report_date is not None:
            data["report_date"] = notification.report_date.isoformat()

        try:
            await send_push(
                token=device.push_token,
                title=notification.title,
                body=notification.body,
                image_url=image_url,
                data=data,
            )
        except messaging.UnregisteredError, messaging.SenderIdMismatchError:
            device.push_token = None

            await db.commit()
        except (
            exceptions.UnavailableError,
            exceptions.InternalError,
            exceptions.ResourceExhaustedError,
            exceptions.DeadlineExceededError,
        ) as exc:
            raise PushDeliveryRetryError from exc
        except exceptions.FirebaseError:
            logger.exception("알림 발송 실패; notification_id=%s", notification_id)
