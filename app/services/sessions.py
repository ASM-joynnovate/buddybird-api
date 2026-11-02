from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid7

from sqlalchemy import and_, case, delete, exists, func, not_, or_, select, union_all
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db import transactional
from app.enums import (
    FeedItemKindEnum,
    FileStatusEnum,
    JudgmentStatusEnum,
    MimicJudgmentStatusEnum,
    ParrotDetectionStatusEnum,
    SessionActorEnum,
    SessionEndReasonEnum,
    SessionEventFileKindEnum,
    SessionEventKindEnum,
    SessionLogKindEnum,
    SessionSoundKindEnum,
    SessionStatusEnum,
)
from app.errors import (
    DeviceNotStationError,
    FileSizeExceededError,
    ResourceNotFoundError,
    SessionAlreadyRunningError,
    SessionJudgmentPendingError,
    SessionNotRunningError,
    SessionSaveUnavailableError,
    UnsupportedSessionEventError,
)
from app.file import build_file_dto
from app.models import (
    Device,
    FeedItem,
    File,
    LearningSegment,
    Session,
    SessionEvent,
    SessionEventFile,
    SessionEventLabel,
    SessionEventSound,
    SessionEventUserReview,
    SessionSound,
    SessionSoundUserReview,
    User,
    Word,
)
from app.s3 import UPLOAD_URL_EXPIRES_IN, S3StorageClient
from app.schemas.base import PageParams, UploadDTO
from app.schemas.sessions import (
    AcknowledgedLearningSegmentDTO,
    ActiveDurationDTO,
    AddSessionEventsRequest,
    BackofficeSessionDisconnectionDTO,
    BackofficeSessionDTO,
    BackofficeSessionEventDetailDTO,
    BackofficeSessionEventDTO,
    BackofficeSessionEventLabelDTO,
    BackofficeSessionEventListParams,
    BackofficeSessionEventUserReviewDTO,
    BackofficeSessionListParams,
    BackofficeSessionPeriodDTO,
    BackofficeSessionWordDTO,
    HeartbeatDTO,
    HeartbeatRequest,
    HeartbeatSessionDTO,
    SessionDTO,
    SessionEventDTO,
    SessionEventsDTO,
    SessionEventWordDTO,
    SessionJudgmentDTO,
    SessionLogDistressCallDTO,
    SessionLogDistressCallSoundDTO,
    SessionLogItemDTO,
    SessionLogListParams,
    SessionLogMimicDTO,
    SessionLogParrotAppearedDTO,
    SessionLogParrotDisappearedDTO,
    SessionLogParrotDTO,
    SessionPeriodDTO,
    SessionPetcamEventRequest,
    SessionPetcamEventUploadDTO,
    SessionPetcamVideoUploadRequest,
    SessionProgressDTO,
    SessionScheduleDTO,
    SessionSoundsDTO,
    SessionStationDTO,
    SessionSummaryDTO,
    SessionSummarySessionDTO,
    SessionSummaryTotalDTO,
    SessionSummaryWordDTO,
    SessionUserReviewDTO,
    SessionWordDTO,
    StartSessionRequest,
    UpdateSessionUserReviewRequest,
)
from app.schemas.settings import SleepSettingsDTO
from app.services.devices import mark_seen
from app.services.feed import record_achievements
from app.services.leaderboard import record_finished_sessions
from app.services.session_periods import get_active_durations
from app.utils import correctness_filter

MAX_PETCAM_PHOTO_BYTES = 5 * 1024 * 1024
PETCAM_PHOTO_TYPE = "image/jpeg"
MAX_PETCAM_VIDEO_BYTES = 100 * 1024 * 1024
PETCAM_VIDEO_TYPE = "video/mp4"
REVIEWABLE_EVENT_KINDS = [
    SessionEventKindEnum.DISTRESS_CALL_DETECTED.value,
    SessionEventKindEnum.PARROT_DISAPPEARED.value,
    SessionEventKindEnum.PARROT_APPEARED.value,
]
SESSION_COUNT = (
    select(func.count())
    .select_from(Session)
    .where(Session.user_id == User.id, Session.is_deleted.is_(False))
    .scalar_subquery()
)
APPEARED_EVENT = aliased(SessionEvent)
APPEARED_EVENT_ID = (
    select(APPEARED_EVENT.id)
    .where(
        APPEARED_EVENT.session_id == SessionEvent.session_id,
        APPEARED_EVENT.kind == SessionEventKindEnum.PARROT_APPEARED.value,
        APPEARED_EVENT.occurred_at > SessionEvent.occurred_at,
        APPEARED_EVENT.is_correct.is_not(False),
    )
    .order_by(APPEARED_EVENT.occurred_at)
    .limit(1)
    .scalar_subquery()
)


def build_session_dto(
    session: Session, judgment_status: JudgmentStatusEnum, sounds: SessionSoundsDTO, events: SessionEventsDTO
) -> SessionDTO:
    return SessionDTO(
        id=session.id,
        status=session.status,
        station=SessionStationDTO(device_id=session.station_device_id),
        word=SessionWordDTO(id=session.word_id),
        schedule=SessionScheduleDTO(
            ends_at=session.scheduled_end_at,
            sleep=SleepSettingsDTO(sleep_at=session.sleep_at, wake_at=session.wake_at)
            if session.sleep_at is not None
            else None,
        ),
        progress=SessionProgressDTO(
            current_phase=session.current_phase,
            phase_started_at=session.phase_started_at,
            last_heartbeat_at=session.last_heartbeat_at,
        ),
        period=SessionPeriodDTO(started_at=session.started_at, ended_at=session.ended_at, ended_by=session.ended_by),
        judgment=SessionJudgmentDTO(status=judgment_status),
        sounds=sounds,
        events=events,
    )


async def get_judgment_statuses(*, db: AsyncSession, sessions: Sequence[Session]) -> dict[UUID, JudgmentStatusEnum]:
    stmt = (
        select(SessionSound.session_id)
        .join(File, File.id == SessionSound.audio_file_id)
        .where(
            SessionSound.session_id.in_(
                [session.id for session in sessions if session.status == SessionStatusEnum.FINISHED.value]
            ),
            File.status == FileStatusEnum.UPLOADED.value,
            or_(
                SessionSound.parrot_detection_status == ParrotDetectionStatusEnum.PENDING.value,
                SessionSound.mimic_judgment_status == MimicJudgmentStatusEnum.PENDING.value,
            ),
        )
        .distinct()
    )
    pending_session_ids = set((await db.scalars(stmt)).all())

    return {
        session.id: JudgmentStatusEnum.PENDING
        if session.status == SessionStatusEnum.RUNNING.value or session.id in pending_session_ids
        else JudgmentStatusEnum.DONE
        for session in sessions
    }


async def get_sound_counts(*, db: AsyncSession, sessions: Sequence[Session]) -> dict[UUID, SessionSoundsDTO]:
    stmt = (
        select(
            SessionSound.session_id,
            func.count(),
            func.count().filter(
                SessionSound.kind.in_([SessionSoundKindEnum.PARROT.value, SessionSoundKindEnum.MIMIC.value])
            ),
            func.count().filter(SessionSound.kind == SessionSoundKindEnum.MIMIC.value),
        )
        .where(SessionSound.session_id.in_([session.id for session in sessions]))
        .group_by(SessionSound.session_id)
    )
    sound_counts = {
        session_id: SessionSoundsDTO(vad_count=vad_count, parrot_count=parrot_count, mimic_count=mimic_count)
        for session_id, vad_count, parrot_count, mimic_count in (await db.execute(stmt)).all()
    }

    return {
        session.id: sound_counts.get(session.id, SessionSoundsDTO(vad_count=0, parrot_count=0, mimic_count=0))
        for session in sessions
    }


async def get_event_counts(*, db: AsyncSession, sessions: Sequence[Session]) -> dict[UUID, SessionEventsDTO]:
    stmt = (
        select(
            SessionEvent.session_id,
            func.count().filter(SessionEvent.kind == SessionEventKindEnum.DISTRESS_CALL_DETECTED.value),
            func.count().filter(SessionEvent.kind == SessionEventKindEnum.PARROT_DISAPPEARED.value),
        )
        .where(
            SessionEvent.session_id.in_([session.id for session in sessions]),
            SessionEvent.is_correct.is_not(False),
        )
        .group_by(SessionEvent.session_id)
    )
    event_counts = {
        session_id: SessionEventsDTO(
            distress_call_count=distress_call_count,
            parrot_disappeared_count=parrot_disappeared_count,
        )
        for session_id, distress_call_count, parrot_disappeared_count in (await db.execute(stmt)).all()
    }

    return {
        session.id: event_counts.get(session.id, SessionEventsDTO(distress_call_count=0, parrot_disappeared_count=0))
        for session in sessions
    }


async def get_event_details(
    *, db: AsyncSession, session: Session
) -> tuple[dict[UUID, list[UUID]], dict[UUID, datetime], dict[UUID, SessionEventUserReview]]:
    stmt = (
        select(SessionEventSound.event_id, SessionSound.id, SessionSound.captured_at)
        .join(SessionSound, SessionSound.id == SessionEventSound.sound_id)
        .where(SessionSound.session_id == session.id)
        .order_by(SessionSound.captured_at)
    )
    sound_ids: dict[UUID, list[UUID]] = {}
    ended_ats: dict[UUID, datetime] = {}

    for event_id, sound_id, captured_at in (await db.execute(stmt)).all():
        sound_ids.setdefault(event_id, []).append(sound_id)

        ended_ats[event_id] = captured_at

    stmt = (
        select(SessionEventUserReview)
        .join(SessionEvent, SessionEvent.id == SessionEventUserReview.session_event_id)
        .where(SessionEvent.session_id == session.id)
    )
    reviews = {review.session_event_id: review for review in (await db.scalars(stmt)).all()}

    return sound_ids, ended_ats, reviews


async def verify_words_owned(*, db: AsyncSession, user_id: UUID, word_ids: set[UUID]) -> None:
    if not word_ids:
        return

    owned = set(
        (
            await db.scalars(
                select(Word.id)
                .where(Word.user_id == user_id, Word.id.in_(word_ids))
                .execution_options(include_deleted=True)
            )
        ).all()
    )

    if word_ids - owned:
        raise ResourceNotFoundError


def verify_running(session: Session) -> None:
    if session.status != SessionStatusEnum.RUNNING.value:
        raise SessionNotRunningError


def verify_station(session: Session, device: Device) -> None:
    if session.station_device_id != device.id:
        raise DeviceNotStationError


async def get_list(*, db: AsyncSession, user: User, query: PageParams) -> tuple[list[SessionDTO], int]:
    stmt = select(Session).where(Session.user_id == user.id)
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    sessions = (
        await db.scalars(
            stmt.order_by(Session.started_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()
    judgment_statuses = await get_judgment_statuses(db=db, sessions=sessions)
    sound_counts = await get_sound_counts(db=db, sessions=sessions)
    event_counts = await get_event_counts(db=db, sessions=sessions)

    return [
        build_session_dto(session, judgment_statuses[session.id], sound_counts[session.id], event_counts[session.id])
        for session in sessions
    ], total


async def get_backoffice_list(
    *, db: AsyncSession, user: User, query: BackofficeSessionListParams
) -> tuple[list[BackofficeSessionDTO], int, int]:
    page = query.page

    if query.session_id is not None:
        stmt = select(Session.started_at).where(Session.id == query.session_id, Session.user_id == user.id)
        started_at = await db.scalar(stmt)

        if started_at is not None:
            stmt = (
                select(func.count())
                .select_from(Session)
                .where(Session.user_id == user.id, Session.started_at > started_at)
            )
            page = await db.scalar(stmt) // query.count_by_page + 1

    stmt = select(Session).where(Session.user_id == user.id)
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    sessions = (
        await db.scalars(
            stmt.order_by(Session.started_at.desc()).offset((page - 1) * query.count_by_page).limit(query.count_by_page)
        )
    ).all()
    session_ids = [session.id for session in sessions]
    judgment_statuses = await get_judgment_statuses(db=db, sessions=sessions)
    sound_counts = await get_sound_counts(db=db, sessions=sessions)
    event_counts = await get_event_counts(db=db, sessions=sessions)

    stmt = (
        select(Word.id, Word.name)
        .where(Word.id.in_({session.word_id for session in sessions}))
        .execution_options(include_deleted=True)
    )
    word_names = dict((await db.execute(stmt)).all())

    stmt = (
        select(SessionEvent.session_id, SessionEvent.kind, SessionEvent.occurred_at)
        .where(
            SessionEvent.session_id.in_(session_ids),
            SessionEvent.kind.in_(
                [
                    SessionEventKindEnum.STATION_DISCONNECTED.value,
                    SessionEventKindEnum.STATION_RECONNECTED.value,
                    SessionEventKindEnum.DISTRESS_CALL_DETECTED.value,
                    SessionEventKindEnum.PARROT_DISAPPEARED.value,
                ]
            ),
        )
        .order_by(SessionEvent.occurred_at)
    )

    if query.label is not None:
        stmt = stmt.where(
            or_(
                SessionEvent.kind.not_in(REVIEWABLE_EVENT_KINDS),
                correctness_filter(SessionEvent.is_correct, query.label),
            )
        )

    events = (await db.execute(stmt)).all()
    disconnected_at: dict[UUID, datetime] = {}
    disconnections: dict[UUID, list[BackofficeSessionDisconnectionDTO]] = {}
    distress_call_detections: dict[UUID, list[datetime]] = {}
    parrot_disappearances: dict[UUID, list[datetime]] = {}

    for session_id, kind, occurred_at in events:
        if kind == SessionEventKindEnum.DISTRESS_CALL_DETECTED.value:
            distress_call_detections.setdefault(session_id, []).append(occurred_at)
        elif kind == SessionEventKindEnum.PARROT_DISAPPEARED.value:
            parrot_disappearances.setdefault(session_id, []).append(occurred_at)
        elif kind == SessionEventKindEnum.STATION_DISCONNECTED.value:
            disconnected_at.setdefault(session_id, occurred_at)
        elif session_id in disconnected_at:
            disconnections.setdefault(session_id, []).append(
                BackofficeSessionDisconnectionDTO(started_at=disconnected_at.pop(session_id), ended_at=occurred_at)
            )

    for session_id, started_at in disconnected_at.items():
        disconnections.setdefault(session_id, []).append(
            BackofficeSessionDisconnectionDTO(started_at=started_at, ended_at=None)
        )

    items = [
        BackofficeSessionDTO(
            **build_session_dto(
                session, judgment_statuses[session.id], sound_counts[session.id], event_counts[session.id]
            ).model_dump(exclude={"word", "period"}),
            word=BackofficeSessionWordDTO(id=session.word_id, name=word_names[session.word_id]),
            period=BackofficeSessionPeriodDTO(
                started_at=session.started_at,
                ended_at=session.ended_at,
                ended_by=session.ended_by,
                ended_reason=session.ended_reason,
            ),
            disconnections=disconnections.get(session.id, []),
            distress_call_detections=distress_call_detections.get(session.id, []),
            parrot_disappearances=parrot_disappearances.get(session.id, []),
        )
        for session in sessions
    ]

    return items, total, page


async def get_detail(*, db: AsyncSession, session: Session) -> SessionDTO:
    judgment_statuses = await get_judgment_statuses(db=db, sessions=[session])
    sound_counts = await get_sound_counts(db=db, sessions=[session])
    event_counts = await get_event_counts(db=db, sessions=[session])

    return build_session_dto(session, judgment_statuses[session.id], sound_counts[session.id], event_counts[session.id])


@transactional(unavailable_error=SessionSaveUnavailableError)
async def start(*, db: AsyncSession, user: User, device: Device, data: StartSessionRequest) -> SessionDTO:
    await verify_words_owned(db=db, user_id=user.id, word_ids={data.word_id})

    now = datetime.now(UTC)
    session = Session(
        user_id=user.id,
        station_device_id=device.id,
        status=SessionStatusEnum.RUNNING.value,
        word_id=data.word_id,
        scheduled_end_at=data.ends_at,
        sleep_at=data.sleep.sleep_at if data.sleep is not None else None,
        wake_at=data.sleep.wake_at if data.sleep is not None else None,
        started_at=now,
        is_deleted=False,
    )

    db.add(session)

    try:
        await db.flush()
    except IntegrityError as exc:
        raise SessionAlreadyRunningError from exc

    db.add(
        SessionEvent(
            session_id=session.id,
            kind=SessionEventKindEnum.SESSION_STARTED.value,
            occurred_at=now,
        )
    )

    await db.flush()

    return build_session_dto(
        session,
        JudgmentStatusEnum.PENDING,
        SessionSoundsDTO(vad_count=0, parrot_count=0, mimic_count=0),
        SessionEventsDTO(distress_call_count=0, parrot_disappeared_count=0),
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def finish(*, db: AsyncSession, session: Session) -> SessionDTO:
    verify_running(session)

    now = datetime.now(UTC)
    session.status = SessionStatusEnum.FINISHED.value
    session.ended_at = now
    session.ended_by = SessionActorEnum.USER.value
    session.ended_reason = SessionEndReasonEnum.USER.value

    db.add(
        SessionEvent(
            session_id=session.id,
            kind=SessionEventKindEnum.SESSION_FINISHED.value,
            occurred_at=now,
        )
    )

    await record_achievements(db=db, sessions=[session], now=now)
    await record_finished_sessions(db=db, sessions=[session])
    await db.flush()

    judgment_statuses = await get_judgment_statuses(db=db, sessions=[session])
    sound_counts = await get_sound_counts(db=db, sessions=[session])
    event_counts = await get_event_counts(db=db, sessions=[session])

    return build_session_dto(session, judgment_statuses[session.id], sound_counts[session.id], event_counts[session.id])


@transactional(unavailable_error=SessionSaveUnavailableError)
async def finish_expired_sessions(*, db: AsyncSession) -> list[UUID]:
    now = datetime.now(UTC)
    heartbeat_deadline = now - timedelta(minutes=1)
    stmt = select(Session).where(
        Session.status == SessionStatusEnum.RUNNING.value,
        or_(
            func.coalesce(Session.last_heartbeat_at, Session.started_at) <= heartbeat_deadline,
            Session.scheduled_end_at <= now,
        ),
    )
    sessions = (await db.scalars(stmt)).all()

    for session in sessions:
        last_active_at = session.last_heartbeat_at if session.last_heartbeat_at is not None else session.started_at
        heartbeat_expired = last_active_at <= heartbeat_deadline
        schedule_expired = session.scheduled_end_at is not None and session.scheduled_end_at <= now

        if heartbeat_expired and schedule_expired:
            ended_at = min(last_active_at, session.scheduled_end_at)
        elif heartbeat_expired:
            ended_at = last_active_at
        else:
            ended_at = session.scheduled_end_at

        session.status = SessionStatusEnum.FINISHED.value
        session.ended_at = ended_at
        session.ended_by = SessionActorEnum.SERVER.value
        session.ended_reason = (
            SessionEndReasonEnum.HEARTBEAT_EXPIRED.value
            if heartbeat_expired and ended_at == last_active_at
            else SessionEndReasonEnum.SCHEDULED.value
        )

        db.add(
            SessionEvent(
                session_id=session.id,
                kind=SessionEventKindEnum.SESSION_FINISHED.value,
                occurred_at=ended_at,
            )
        )

    await record_achievements(db=db, sessions=sessions, now=now)
    await record_finished_sessions(db=db, sessions=sessions)
    await db.flush()

    return [session.id for session in sessions]


@transactional(unavailable_error=SessionSaveUnavailableError)
async def record_heartbeat(
    *, db: AsyncSession, session: Session, device: Device, data: HeartbeatRequest, country: str | None
) -> HeartbeatDTO:
    verify_station(session, device)
    verify_running(session)

    now = datetime.now(UTC)
    session.current_phase = data.current_phase.value if data.current_phase is not None else None
    session.phase_started_at = data.phase_started_at
    session.last_heartbeat_at = now

    await mark_seen(db=db, device=device, country=country)

    segments: dict[tuple[UUID, datetime], dict] = {}

    for segment in data.learning_segments:
        current = segments.get((segment.word_id, segment.started_at))

        if current is None:
            segments[(segment.word_id, segment.started_at)] = {
                "session_id": session.id,
                "word_id": segment.word_id,
                "started_at": segment.started_at,
                "ended_at": segment.ended_at,
                "play_count": segment.play_count,
                "play_duration_ms": segment.play_duration_ms,
            }
        else:
            current["ended_at"] = max(current["ended_at"], segment.ended_at)
            current["play_count"] = max(current["play_count"], segment.play_count)
            current["play_duration_ms"] = max(current["play_duration_ms"], segment.play_duration_ms)

    if segments:
        await verify_words_owned(db=db, user_id=session.user_id, word_ids={word_id for word_id, _ in segments})

        stmt = insert(LearningSegment).values(list(segments.values()))
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    LearningSegment.session_id,
                    LearningSegment.word_id,
                    LearningSegment.started_at,
                ],
                set_={
                    "ended_at": func.greatest(LearningSegment.ended_at, stmt.excluded.ended_at),
                    "play_count": func.greatest(LearningSegment.play_count, stmt.excluded.play_count),
                    "play_duration_ms": func.greatest(LearningSegment.play_duration_ms, stmt.excluded.play_duration_ms),
                },
            )
        )

    await db.flush()

    return HeartbeatDTO(
        session=HeartbeatSessionDTO(status=session.status),
        acknowledged=[
            AcknowledgedLearningSegmentDTO(word_id=word_id, started_at=started_at) for word_id, started_at in segments
        ],
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def add_events(*, db: AsyncSession, session: Session, data: AddSessionEventsRequest) -> None:
    await verify_words_owned(
        db=db,
        user_id=session.user_id,
        word_ids={event.word_id for event in data.events if event.word_id is not None},
    )

    for event in data.events:
        db.add(
            SessionEvent(
                session_id=session.id,
                kind=event.kind.value,
                occurred_at=event.occurred_at,
                word_id=event.word_id,
            )
        )

    await db.flush()


@transactional(unavailable_error=SessionSaveUnavailableError)
async def add_petcam_event(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    session: Session,
    device: Device,
    data: SessionPetcamEventRequest,
) -> SessionPetcamEventUploadDTO:
    verify_station(session, device)

    if data.file_size > MAX_PETCAM_PHOTO_BYTES:
        raise FileSizeExceededError

    file_id = uuid7()
    image_file = File(
        id=file_id,
        file_name="petcam.jpg",
        file_path=f"user/{session.user_id}/petcam/{session.id}/{file_id}",
        file_size=data.file_size,
        file_type=PETCAM_PHOTO_TYPE,
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )
    event = SessionEvent(
        session_id=session.id,
        kind=data.kind.value,
        occurred_at=data.occurred_at,
    )

    db.add(image_file)
    db.add(event)

    await db.flush()

    db.add(SessionEventFile(event_id=event.id, kind=SessionEventFileKindEnum.IMAGE.value, file=image_file))

    await db.flush()

    upload = storage.generate_presigned_upload(
        file_id=file_id,
        path=image_file.object_key,
        content_type=PETCAM_PHOTO_TYPE,
        file_size=data.file_size,
    )

    return SessionPetcamEventUploadDTO(**upload.model_dump(), event_id=event.id)


@transactional(unavailable_error=SessionSaveUnavailableError)
async def add_petcam_video(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    session: Session,
    device: Device,
    event_id: UUID,
    data: SessionPetcamVideoUploadRequest,
) -> UploadDTO:
    verify_station(session, device)

    if data.file_size > MAX_PETCAM_VIDEO_BYTES:
        raise FileSizeExceededError

    stmt = select(SessionEvent.id).where(SessionEvent.id == event_id, SessionEvent.session_id == session.id)

    if await db.scalar(stmt) is None:
        raise ResourceNotFoundError

    file_id = uuid7()
    video_file = File(
        id=file_id,
        file_name="petcam.mp4",
        file_path=f"user/{session.user_id}/petcam/{session.id}/{file_id}",
        file_size=data.file_size,
        file_type=PETCAM_VIDEO_TYPE,
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )

    db.add(video_file)

    stmt = select(SessionEventFile).where(
        SessionEventFile.event_id == event_id, SessionEventFile.kind == SessionEventFileKindEnum.VIDEO.value
    )
    event_file = await db.scalar(stmt)

    if event_file is None:
        db.add(SessionEventFile(event_id=event_id, kind=SessionEventFileKindEnum.VIDEO.value, file=video_file))
    else:
        event_file.file = video_file

    await db.flush()

    return storage.generate_presigned_upload(
        file_id=file_id,
        path=video_file.object_key,
        content_type=PETCAM_VIDEO_TYPE,
        file_size=data.file_size,
    )


async def get_events(
    *, db: AsyncSession, storage: S3StorageClient, session: Session, petcam: bool, distress_call: bool
) -> list[SessionEventDTO]:
    stmt = (
        select(SessionEvent)
        .where(SessionEvent.session_id == session.id, SessionEvent.is_correct.is_not(False))
        .order_by(SessionEvent.occurred_at)
    )

    if not petcam:
        stmt = stmt.where(
            SessionEvent.kind.not_in(
                [SessionEventKindEnum.PARROT_DISAPPEARED.value, SessionEventKindEnum.PARROT_APPEARED.value]
            )
        )

    if not distress_call:
        stmt = stmt.where(SessionEvent.kind != SessionEventKindEnum.DISTRESS_CALL_DETECTED.value)

    events = (await db.scalars(stmt)).all()
    sound_ids, ended_ats, reviews = await get_event_details(db=db, session=session)
    appeared_ats = [event.occurred_at for event in events if event.kind == SessionEventKindEnum.PARROT_APPEARED.value]

    for event in events:
        if event.kind == SessionEventKindEnum.PARROT_DISAPPEARED.value:
            ended_at = next((at for at in appeared_ats if at > event.occurred_at), None)

            if ended_at is not None:
                ended_ats[event.id] = ended_at

    stmt = (
        select(SessionEventFile)
        .join(SessionEvent, SessionEvent.id == SessionEventFile.event_id)
        .where(SessionEvent.session_id == session.id)
    )
    files = {(event_file.event_id, event_file.kind): event_file.file for event_file in (await db.scalars(stmt)).all()}

    return [
        SessionEventDTO(
            id=event.id,
            kind=event.kind,
            occurred_at=event.occurred_at,
            ended_at=ended_ats.get(event.id),
            word=SessionEventWordDTO(id=event.word_id) if event.word_id is not None else None,
            sound_ids=sound_ids.get(event.id, []),
            image=build_file_dto(storage=storage, file=files.get((event.id, SessionEventFileKindEnum.IMAGE.value))),
            video=build_file_dto(storage=storage, file=files.get((event.id, SessionEventFileKindEnum.VIDEO.value))),
            user_review=SessionUserReviewDTO(is_correct=reviews[event.id].is_correct) if event.id in reviews else None,
        )
        for event in events
    ]


async def get_log(
    *, db: AsyncSession, storage: S3StorageClient, session: Session, query: SessionLogListParams
) -> tuple[list[SessionLogItemDTO], int]:
    distress_call_sound = (
        select(SessionEventSound.sound_id)
        .join(SessionEvent, SessionEvent.id == SessionEventSound.event_id)
        .where(
            SessionEventSound.sound_id == SessionSound.id,
            SessionEvent.kind == SessionEventKindEnum.DISTRESS_CALL_DETECTED.value,
            SessionEvent.is_correct.is_not(False),
        )
    )
    sound_stmt = (
        select(
            SessionSound.id,
            case(
                (SessionSound.kind == SessionSoundKindEnum.MIMIC.value, SessionLogKindEnum.MIMIC.value),
                else_=SessionLogKindEnum.PARROT.value,
            ).label("kind"),
            SessionSound.captured_at.label("occurred_at"),
        )
        .join(File, File.id == SessionSound.audio_file_id)
        .where(
            SessionSound.session_id == session.id,
            SessionSound.kind.is_distinct_from(SessionSoundKindEnum.NOT_PARROT.value),
            SessionSound.parrot_detection_status != ParrotDetectionStatusEnum.FAILED.value,
            or_(
                File.status == FileStatusEnum.UPLOADED.value,
                and_(
                    File.status == FileStatusEnum.PENDING.value,
                    File.created_at > datetime.now(UTC) - timedelta(seconds=UPLOAD_URL_EXPIRES_IN),
                ),
            ),
            or_(SessionSound.kind == SessionSoundKindEnum.MIMIC.value, not_(exists(distress_call_sound))),
        )
    )
    event_stmt = select(SessionEvent.id, SessionEvent.kind, SessionEvent.occurred_at).where(
        SessionEvent.session_id == session.id,
        SessionEvent.kind.in_(REVIEWABLE_EVENT_KINDS),
        SessionEvent.is_correct.is_not(False),
    )
    subquery = union_all(sound_stmt, event_stmt).subquery()

    stmt = select(subquery.c.id, subquery.c.kind).where(subquery.c.kind.in_(query.kind))
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    rows = (
        await db.execute(
            stmt.order_by(subquery.c.occurred_at, subquery.c.id)
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()
    sound_ids = [row.id for row in rows if row.kind in (SessionLogKindEnum.PARROT, SessionLogKindEnum.MIMIC)]
    event_ids = [row.id for row in rows if row.kind in REVIEWABLE_EVENT_KINDS]

    stmt = select(SessionSound).where(SessionSound.id.in_(sound_ids))
    sounds = (await db.scalars(stmt)).all()

    stmt = select(SessionSoundUserReview).where(SessionSoundUserReview.session_sound_id.in_(sound_ids))
    sound_reviews = {review.session_sound_id: review for review in (await db.scalars(stmt)).all()}

    stmt = (
        select(FeedItem.file_id)
        .where(
            FeedItem.kind == FeedItemKindEnum.MIMIC_SUCCEEDED.value,
            FeedItem.file_id.in_([sound.audio_file_id for sound in sounds]),
        )
        .execution_options(include_deleted=True)
    )
    shared_file_ids = set((await db.scalars(stmt)).all())

    appeared_event = aliased(SessionEvent)
    stmt = (
        select(SessionEvent, appeared_event.occurred_at)
        .outerjoin(appeared_event, appeared_event.id == APPEARED_EVENT_ID)
        .where(SessionEvent.id.in_(event_ids))
    )
    events = (await db.execute(stmt)).all()

    stmt = select(SessionEventUserReview).where(SessionEventUserReview.session_event_id.in_(event_ids))
    event_reviews = {review.session_event_id: review for review in (await db.scalars(stmt)).all()}

    stmt = select(SessionEventFile).where(SessionEventFile.event_id.in_(event_ids))
    files = {(event_file.event_id, event_file.kind): event_file.file for event_file in (await db.scalars(stmt)).all()}

    stmt = (
        select(SessionEventSound.event_id, SessionSound)
        .join(SessionSound, SessionSound.id == SessionEventSound.sound_id)
        .where(SessionEventSound.event_id.in_(event_ids))
        .order_by(SessionSound.captured_at)
    )
    event_sounds: dict[UUID, list[SessionSound]] = {}

    for event_id, sound in (await db.execute(stmt)).all():
        event_sounds.setdefault(event_id, []).append(sound)

    items: dict[UUID, SessionLogItemDTO] = {}

    for sound in sounds:
        review = sound_reviews.get(sound.id)
        user_review = (
            SessionUserReviewDTO(is_correct=review.is_correct)
            if review is not None and review.kind == sound.kind
            else None
        )

        if sound.kind == SessionSoundKindEnum.MIMIC:
            items[sound.id] = SessionLogMimicDTO(
                id=sound.id,
                kind=SessionLogKindEnum.MIMIC,
                occurred_at=sound.captured_at,
                audio_file=build_file_dto(storage=storage, file=sound.audio_file),
                duration_ms=sound.duration_ms,
                score=sound.final_mimic_score,
                is_feed_shared=sound.audio_file_id in shared_file_ids,
                user_review=user_review,
            )
        else:
            items[sound.id] = SessionLogParrotDTO(
                id=sound.id,
                kind=SessionLogKindEnum.PARROT,
                occurred_at=sound.captured_at,
                audio_file=build_file_dto(storage=storage, file=sound.audio_file),
                duration_ms=sound.duration_ms,
                score=sound.final_parrot_score,
                user_review=user_review,
            )

    for event, appeared_at in events:
        user_review = (
            SessionUserReviewDTO(is_correct=event_reviews[event.id].is_correct) if event.id in event_reviews else None
        )

        if event.kind == SessionEventKindEnum.DISTRESS_CALL_DETECTED.value:
            items[event.id] = SessionLogDistressCallDTO(
                id=event.id,
                kind=SessionLogKindEnum.DISTRESS_CALL_DETECTED,
                occurred_at=event.occurred_at,
                ended_at=event_sounds[event.id][-1].captured_at,
                sounds=[
                    SessionLogDistressCallSoundDTO(
                        id=sound.id,
                        captured_at=sound.captured_at,
                        audio_file=build_file_dto(storage=storage, file=sound.audio_file),
                        duration_ms=sound.duration_ms,
                    )
                    for sound in event_sounds[event.id]
                ],
                user_review=user_review,
            )
        elif event.kind == SessionEventKindEnum.PARROT_DISAPPEARED.value:
            items[event.id] = SessionLogParrotDisappearedDTO(
                id=event.id,
                kind=SessionLogKindEnum.PARROT_DISAPPEARED,
                occurred_at=event.occurred_at,
                ended_at=appeared_at,
                image=build_file_dto(storage=storage, file=files.get((event.id, SessionEventFileKindEnum.IMAGE.value))),
                video=build_file_dto(storage=storage, file=files.get((event.id, SessionEventFileKindEnum.VIDEO.value))),
                user_review=user_review,
            )
        else:
            items[event.id] = SessionLogParrotAppearedDTO(
                id=event.id,
                kind=SessionLogKindEnum.PARROT_APPEARED,
                occurred_at=event.occurred_at,
                image=build_file_dto(storage=storage, file=files.get((event.id, SessionEventFileKindEnum.IMAGE.value))),
                user_review=user_review,
            )

    return [items[row.id] for row in rows], total


async def get_backoffice_events(
    *, db: AsyncSession, storage: S3StorageClient, session: Session, query: BackofficeSessionEventListParams
) -> list[BackofficeSessionEventDTO]:
    stmt = (
        select(SessionEvent, Word.name)
        .outerjoin(Word, Word.id == SessionEvent.word_id)
        .where(SessionEvent.session_id == session.id)
        .order_by(SessionEvent.occurred_at)
        .execution_options(include_deleted=True)
    )

    if query.label is not None:
        stmt = stmt.where(
            or_(
                SessionEvent.kind.not_in(REVIEWABLE_EVENT_KINDS),
                correctness_filter(SessionEvent.is_correct, query.label),
            )
        )

    rows = (await db.execute(stmt)).all()
    sound_ids, ended_ats, reviews = await get_event_details(db=db, session=session)

    stmt = (
        select(SessionEventFile)
        .join(SessionEvent, SessionEvent.id == SessionEventFile.event_id)
        .where(SessionEvent.session_id == session.id)
    )
    files = {(event_file.event_id, event_file.kind): event_file.file for event_file in (await db.scalars(stmt)).all()}
    toggle_count = 0
    items = []

    for event, word_name in rows:
        is_learning = None

        if event.kind == SessionEventKindEnum.LEARNING_TOGGLED.value:
            toggle_count += 1
            is_learning = toggle_count % 2 == 0

        items.append(
            BackofficeSessionEventDTO(
                id=event.id,
                kind=event.kind,
                occurred_at=event.occurred_at,
                ended_at=ended_ats.get(event.id),
                word=BackofficeSessionWordDTO(id=event.word_id, name=word_name) if event.word_id is not None else None,
                sound_ids=sound_ids.get(event.id, []),
                image=build_file_dto(storage=storage, file=files.get((event.id, SessionEventFileKindEnum.IMAGE.value))),
                video=build_file_dto(storage=storage, file=files.get((event.id, SessionEventFileKindEnum.VIDEO.value))),
                user_review=BackofficeSessionEventUserReviewDTO(
                    is_correct=reviews[event.id].is_correct,
                    updated_at=reviews[event.id].updated_at,
                )
                if event.id in reviews
                else None,
                is_learning=is_learning,
                is_correct=event.is_correct,
            )
        )

    return items


async def get_backoffice_event(*, db: AsyncSession, event: SessionEvent) -> BackofficeSessionEventDetailDTO:
    stmt = (
        select(SessionEventLabel)
        .where(SessionEventLabel.session_event_id == event.id)
        .order_by(SessionEventLabel.created_at, SessionEventLabel.id)
    )
    labels = (await db.scalars(stmt)).all()

    stmt = select(SessionEventUserReview).where(SessionEventUserReview.session_event_id == event.id)
    review = await db.scalar(stmt)

    return BackofficeSessionEventDetailDTO(
        id=event.id,
        kind=event.kind,
        occurred_at=event.occurred_at,
        is_correct=event.is_correct,
        labels=[
            BackofficeSessionEventLabelDTO(
                id=label.id,
                is_correct=label.is_correct,
                operator_name=label.operator_name,
                memo=label.memo,
                created_at=label.created_at,
            )
            for label in labels
        ],
        user_review=BackofficeSessionEventUserReviewDTO(is_correct=review.is_correct, updated_at=review.updated_at)
        if review is not None
        else None,
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def update_event_user_review(
    *, db: AsyncSession, event: SessionEvent, data: UpdateSessionUserReviewRequest
) -> None:
    if event.kind not in REVIEWABLE_EVENT_KINDS:
        raise UnsupportedSessionEventError

    stmt = insert(SessionEventUserReview).values(session_event_id=event.id, is_correct=data.is_correct)

    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[SessionEventUserReview.session_event_id],
            set_={"is_correct": stmt.excluded.is_correct, "updated_at": func.now()},
        )
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def delete_event_user_review(*, db: AsyncSession, event: SessionEvent) -> None:
    await db.execute(delete(SessionEventUserReview).where(SessionEventUserReview.session_event_id == event.id))


@transactional(unavailable_error=SessionSaveUnavailableError)
async def add_event_label(
    *,
    db: AsyncSession,
    session: Session,
    event: SessionEvent,
    is_correct: bool | None,
    memo: str | None,
    operator_name: str,
) -> None:
    if event.kind not in REVIEWABLE_EVENT_KINDS:
        raise UnsupportedSessionEventError

    if event.kind == SessionEventKindEnum.DISTRESS_CALL_DETECTED:
        judgment_statuses = await get_judgment_statuses(db=db, sessions=[session])

        if judgment_statuses[session.id] == JudgmentStatusEnum.PENDING:
            raise SessionJudgmentPendingError

    db.add(
        SessionEventLabel(
            session_event_id=event.id,
            is_correct=is_correct,
            operator_name=operator_name,
            memo=memo,
        )
    )

    event.is_correct = is_correct

    await db.flush()


async def get_summary(*, db: AsyncSession, session: Session) -> SessionSummaryDTO:
    stmt = select(Word).where(Word.id == session.word_id).execution_options(include_deleted=True)
    word = await db.scalar(stmt)

    stmt = select(func.sum(LearningSegment.play_count)).where(LearningSegment.session_id == session.id)
    play_count = await db.scalar(stmt)

    stmt = select(Session).where(Session.user_id == session.user_id)
    user_sessions = (await db.scalars(stmt)).all()
    durations = await get_active_durations(db=db, sessions=user_sessions)
    word_duration = sum(
        durations[user_session.id] for user_session in user_sessions if user_session.word_id == session.word_id
    )

    return SessionSummaryDTO(
        word=SessionSummaryWordDTO(id=word.id, name=word.name, active=ActiveDurationDTO(duration_ms=word_duration)),
        session=SessionSummarySessionDTO(
            play_count=play_count or 0,
            active=ActiveDurationDTO(duration_ms=durations[session.id]),
        ),
        total=SessionSummaryTotalDTO(active=ActiveDurationDTO(duration_ms=sum(durations.values()))),
    )
