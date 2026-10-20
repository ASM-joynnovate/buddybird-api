from datetime import datetime, time, timedelta
from uuid import UUID

from sqlalchemy import and_, case, exists, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.enums import (
    EmergencyNotificationEnum,
    NotificationKindEnum,
    SessionEventFileKindEnum,
    SessionEventKindEnum,
    SessionStatusEnum,
)
from app.file import build_file_dto
from app.models import (
    Device,
    Notification,
    Parrot,
    ParrotDetection,
    Session,
    SessionEvent,
    SessionEventFile,
    SessionEventSound,
    SessionSound,
    User,
)
from app.s3 import S3StorageClient
from app.schemas.emergencies import (
    BackofficeEmergencyAppearedDTO,
    BackofficeEmergencyDeviceDTO,
    BackofficeEmergencyDTO,
    BackofficeEmergencyListParams,
    BackofficeEmergencyNotificationDTO,
    BackofficeEmergencySessionDTO,
    BackofficeEmergencySessionSoundDTO,
    BackofficeEmergencySoundDTO,
    BackofficeEmergencyUserDTO,
    BackofficeEmergencyVisionDTO,
)
from app.schemas.sessions import SessionSoundAnalysisDTO
from app.schemas.users import BackofficeUserParrotDTO
from app.utils import SEOUL

EMERGENCY_KINDS = [
    SessionEventKindEnum.DISTRESS_CALL_DETECTED.value,
    SessionEventKindEnum.PARROT_DISAPPEARED.value,
]
APPEARED_EVENT = aliased(SessionEvent)
APPEARED_EVENT_ID = (
    select(APPEARED_EVENT.id)
    .where(
        APPEARED_EVENT.session_id == SessionEvent.session_id,
        APPEARED_EVENT.kind == SessionEventKindEnum.PARROT_APPEARED.value,
        APPEARED_EVENT.occurred_at > SessionEvent.occurred_at,
    )
    .order_by(APPEARED_EVENT.occurred_at)
    .limit(1)
    .scalar_subquery()
)
IS_ONGOING = and_(
    SessionEvent.kind == SessionEventKindEnum.PARROT_DISAPPEARED.value,
    Session.status == SessionStatusEnum.RUNNING.value,
    APPEARED_EVENT_ID.is_(None),
)
EVENT_NOTIFICATION = (
    select(Notification.id)
    .join(SessionEventFile, SessionEventFile.file_id == Notification.image_file_id)
    .where(
        SessionEventFile.event_id == SessionEvent.id,
        SessionEventFile.kind == SessionEventFileKindEnum.IMAGE.value,
        Notification.kind == NotificationKindEnum.EMERGENCY.value,
    )
)
NOTIFICATION_STATUS = case(
    (exists(EVENT_NOTIFICATION.where(Notification.read_at.is_not(None))), EmergencyNotificationEnum.READ.value),
    (exists(EVENT_NOTIFICATION), EmergencyNotificationEnum.UNREAD.value),
    else_=EmergencyNotificationEnum.NONE.value,
)


async def get_backoffice_list(
    *, db: AsyncSession, storage: S3StorageClient, query: BackofficeEmergencyListParams
) -> tuple[list[BackofficeEmergencyDTO], int]:
    conditions = [SessionEvent.kind.in_(EMERGENCY_KINDS)]

    if query.occurred_from is not None:
        conditions.append(SessionEvent.occurred_at >= datetime.combine(query.occurred_from, time(0), tzinfo=SEOUL))

    if query.occurred_to is not None:
        conditions.append(
            SessionEvent.occurred_at < datetime.combine(query.occurred_to + timedelta(days=1), time(0), tzinfo=SEOUL)
        )

    if query.kind is not None:
        conditions.append(SessionEvent.kind == query.kind.value)

    if query.keyword is not None:
        conditions.append(
            or_(
                User.nickname.icontains(query.keyword, autoescape=True),
                User.email.icontains(query.keyword, autoescape=True),
            )
        )

    if query.user_id is not None:
        conditions.append(Session.user_id == query.user_id)

    if query.is_ongoing is not None:
        conditions.append(IS_ONGOING if query.is_ongoing else not_(IS_ONGOING))

    if query.notification is not None:
        conditions.append(SessionEvent.kind == SessionEventKindEnum.PARROT_DISAPPEARED.value)

        conditions.append(query.notification.value == NOTIFICATION_STATUS)

    if query.platform is not None:
        conditions.append(Device.platform == query.platform.value)

    stmt = (
        select(func.count())
        .select_from(SessionEvent)
        .join(Session, Session.id == SessionEvent.session_id)
        .join(User, User.id == Session.user_id)
        .join(Device, Device.id == Session.station_device_id)
        .where(*conditions)
        .execution_options(include_deleted=True)
    )
    total = await db.scalar(stmt)

    appeared_event = aliased(SessionEvent, name="appeared")
    stmt = (
        select(SessionEvent, Session, User, Device, appeared_event)
        .select_from(SessionEvent)
        .join(Session, Session.id == SessionEvent.session_id)
        .join(User, User.id == Session.user_id)
        .join(Device, Device.id == Session.station_device_id)
        .outerjoin(appeared_event, appeared_event.id == APPEARED_EVENT_ID)
        .where(*conditions)
        .order_by(SessionEvent.occurred_at.desc())
        .offset((query.page - 1) * query.count_by_page)
        .limit(query.count_by_page)
        .execution_options(include_deleted=True)
    )
    rows = (await db.execute(stmt)).all()
    event_ids = [row.SessionEvent.id for row in rows]
    petcam_event_ids = event_ids + [row.appeared.id for row in rows if row.appeared is not None]

    stmt = select(SessionEventFile).where(SessionEventFile.event_id.in_(petcam_event_ids))
    files = {(event_file.event_id, event_file.kind): event_file.file for event_file in (await db.scalars(stmt)).all()}

    stmt = (
        select(SessionEventFile.event_id, Notification.sent_at, Notification.read_at)
        .select_from(Notification)
        .join(SessionEventFile, SessionEventFile.file_id == Notification.image_file_id)
        .where(
            SessionEventFile.event_id.in_(petcam_event_ids),
            SessionEventFile.kind == SessionEventFileKindEnum.IMAGE.value,
            Notification.kind == NotificationKindEnum.EMERGENCY.value,
        )
        .execution_options(include_deleted=True)
    )
    notifications = {
        event_id: BackofficeEmergencyNotificationDTO(sent_at=sent_at, read_at=read_at)
        for event_id, sent_at, read_at in (await db.execute(stmt)).all()
    }

    stmt = (
        select(SessionEventSound.event_id, SessionSound)
        .join(SessionSound, SessionSound.id == SessionEventSound.sound_id)
        .where(SessionEventSound.event_id.in_(event_ids))
        .order_by(SessionSound.captured_at)
    )
    sounds: dict[UUID, list[SessionSound]] = {}

    for event_id, sound in (await db.execute(stmt)).all():
        sounds.setdefault(event_id, []).append(sound)

    stmt = (
        select(ParrotDetection.sound_id, ParrotDetection.score, ParrotDetection.chirp_count)
        .distinct(ParrotDetection.sound_id)
        .join(SessionEventSound, SessionEventSound.sound_id == ParrotDetection.sound_id)
        .where(SessionEventSound.event_id.in_(event_ids))
        .order_by(ParrotDetection.sound_id, ParrotDetection.analyzed_at.desc())
    )
    analyses = {analysis.sound_id: analysis for analysis in (await db.execute(stmt)).all()}

    stmt = select(Parrot).where(Parrot.user_id.in_({row.User.id for row in rows})).order_by(Parrot.created_at)
    parrots: dict[UUID, list[Parrot]] = {}

    for parrot in (await db.scalars(stmt)).all():
        parrots.setdefault(parrot.user_id, []).append(parrot)

    items = []

    for row in rows:
        event = row.SessionEvent
        user_parrots = parrots.get(row.User.id, [])
        ended_at = None
        sound_dto = None
        vision_dto = None

        if event.kind == SessionEventKindEnum.DISTRESS_CALL_DETECTED.value:
            event_sounds = sounds.get(event.id, [])

            if event_sounds:
                ended_at = event_sounds[-1].captured_at

            sound_dto = BackofficeEmergencySoundDTO(
                sounds=[
                    BackofficeEmergencySessionSoundDTO(
                        id=sound.id,
                        captured_at=sound.captured_at,
                        audio_file=build_file_dto(storage=storage, file=sound.audio_file),
                        duration_ms=sound.duration_ms,
                        analysis=SessionSoundAnalysisDTO(score=analyses[sound.id].score)
                        if sound.id in analyses
                        else None,
                    )
                    for sound in event_sounds
                ],
                chirp_count=sum(analyses[sound.id].chirp_count for sound in event_sounds if sound.id in analyses),
            )
        else:
            appeared_dto = None

            if row.appeared is not None:
                ended_at = row.appeared.occurred_at

                appeared_dto = BackofficeEmergencyAppearedDTO(
                    occurred_at=row.appeared.occurred_at,
                    image=build_file_dto(
                        storage=storage,
                        file=files.get((row.appeared.id, SessionEventFileKindEnum.IMAGE.value)),
                    ),
                    notification=notifications.get(row.appeared.id),
                )

            vision_dto = BackofficeEmergencyVisionDTO(
                image=build_file_dto(storage=storage, file=files.get((event.id, SessionEventFileKindEnum.IMAGE.value))),
                video=build_file_dto(storage=storage, file=files.get((event.id, SessionEventFileKindEnum.VIDEO.value))),
                notification=notifications.get(event.id),
                appeared=appeared_dto,
            )

        items.append(
            BackofficeEmergencyDTO(
                id=event.id,
                kind=event.kind,
                occurred_at=event.occurred_at,
                ended_at=ended_at,
                session=BackofficeEmergencySessionDTO(
                    id=row.Session.id,
                    status=row.Session.status,
                    started_at=row.Session.started_at,
                    ended_at=row.Session.ended_at,
                ),
                user=BackofficeEmergencyUserDTO(
                    id=row.User.id,
                    nickname=row.User.nickname,
                    email=row.User.email,
                    is_anonymous=row.User.is_anonymous,
                    is_deleted=row.User.is_deleted,
                    photo_file=build_file_dto(storage=storage, file=row.User.photo_file),
                ),
                parrot=BackofficeUserParrotDTO(
                    name=user_parrots[0].name,
                    species=user_parrots[0].species,
                    photo_file=build_file_dto(storage=storage, file=user_parrots[0].photo_file),
                )
                if user_parrots
                else None,
                parrot_count=len(user_parrots),
                device=BackofficeEmergencyDeviceDTO(
                    platform=row.Device.platform,
                    model=row.Device.model,
                    app_version=row.Device.app_version,
                ),
                sound=sound_dto,
                vision=vision_dto,
            )
        )

    return items, total
