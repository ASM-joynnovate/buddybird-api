from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import case, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import (
    FileStatusEnum,
    JudgmentStatusEnum,
    SessionActorEnum,
    SessionEndReasonEnum,
    SessionEventKindEnum,
    SessionStatusEnum,
    SoundJudgmentStatusEnum,
)
from app.errors import (
    DeviceNotStationError,
    ResourceNotFoundError,
    SessionAlreadyRunningError,
    SessionNotRunningError,
    SessionSaveUnavailableError,
)
from app.models import Device, File, LearningSegment, Session, SessionEvent, SessionSound, SoundJudgment, User, Word
from app.schemas.base import PageParams
from app.schemas.sessions import (
    AcknowledgedLearningSegmentDTO,
    ActiveDurationDTO,
    AddSessionEventsRequest,
    BackofficeSessionDisconnectionDTO,
    BackofficeSessionDTO,
    BackofficeSessionEventDTO,
    BackofficeSessionPeriodDTO,
    BackofficeSessionSoundsDTO,
    BackofficeSessionWordDTO,
    HeartbeatDTO,
    HeartbeatRequest,
    HeartbeatSessionDTO,
    SessionDTO,
    SessionEventDTO,
    SessionEventWordDTO,
    SessionJudgmentDTO,
    SessionPeriodDTO,
    SessionProgressDTO,
    SessionScheduleDTO,
    SessionStationDTO,
    SessionSummaryDTO,
    SessionSummarySessionDTO,
    SessionSummaryTotalDTO,
    SessionSummaryWordDTO,
    SessionWordDTO,
    StartSessionRequest,
)
from app.schemas.settings import SleepSettingsDTO

LATEST_JUDGED_WORD_ID = (
    select(SoundJudgment.word_id)
    .where(SoundJudgment.sound_id == SessionSound.id)
    .order_by(SoundJudgment.judged_at.desc())
    .limit(1)
    .scalar_subquery()
)


def build_session_dto(session: Session, judgment_status: JudgmentStatusEnum) -> SessionDTO:
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
            SessionSound.judgment_status == SoundJudgmentStatusEnum.PENDING.value,
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


async def get_active_periods(
    *, db: AsyncSession, sessions: Sequence[Session]
) -> dict[UUID, list[tuple[datetime, datetime]]]:
    stmt = (
        select(Device.id, Device.timezone)
        .where(Device.id.in_({session.station_device_id for session in sessions}))
        .execution_options(include_deleted=True)
    )
    timezones = dict((await db.execute(stmt)).all())
    now = datetime.now(UTC)
    active_periods = {}

    for session in sessions:
        ended_at = session.ended_at or now

        if session.sleep_at is None or session.sleep_at == session.wake_at:
            active_periods[session.id] = [(session.started_at, ended_at)]
            continue

        try:
            zone = ZoneInfo(timezones[session.station_device_id] or "UTC")
        except ZoneInfoNotFoundError, ValueError:
            zone = ZoneInfo("UTC")

        periods = []
        active_from = session.started_at
        day = session.started_at.astimezone(zone).date() - timedelta(days=1)

        while active_from < ended_at:
            sleep_from = datetime.combine(day, session.sleep_at, tzinfo=zone)
            wake_day = day if session.wake_at > session.sleep_at else day + timedelta(days=1)
            sleep_until = datetime.combine(wake_day, session.wake_at, tzinfo=zone)

            if sleep_until > active_from:
                if sleep_from > active_from:
                    periods.append((active_from, min(sleep_from, ended_at)))

                active_from = max(active_from, sleep_until)

            day += timedelta(days=1)

        active_periods[session.id] = periods

    return active_periods


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

    return [build_session_dto(session, judgment_statuses[session.id]) for session in sessions], total


async def get_backoffice_list(
    *, db: AsyncSession, user: User, query: PageParams
) -> tuple[list[BackofficeSessionDTO], int]:
    stmt = select(Session).where(Session.user_id == user.id)
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    sessions = (
        await db.scalars(
            stmt.order_by(Session.started_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()
    session_ids = [session.id for session in sessions]
    judgment_statuses = await get_judgment_statuses(db=db, sessions=sessions)

    stmt = (
        select(Word.id, Word.name)
        .where(Word.id.in_({session.word_id for session in sessions}))
        .execution_options(include_deleted=True)
    )
    word_names = dict((await db.execute(stmt)).all())

    stmt = (
        select(
            SessionSound.session_id,
            func.count().filter(SessionSound.is_parrot_sound.is_(True)),
            func.count().filter(LATEST_JUDGED_WORD_ID.is_not(None)),
        )
        .where(SessionSound.session_id.in_(session_ids))
        .group_by(SessionSound.session_id)
    )
    sound_counts = {
        session_id: (parrot_count, mimicry_count)
        for session_id, parrot_count, mimicry_count in (await db.execute(stmt)).all()
    }

    stmt = (
        select(SessionEvent.session_id, SessionEvent.kind, SessionEvent.occurred_at)
        .where(
            SessionEvent.session_id.in_(session_ids),
            SessionEvent.kind.in_(
                [
                    SessionEventKindEnum.STATION_DISCONNECTED.value,
                    SessionEventKindEnum.STATION_RECONNECTED.value,
                    SessionEventKindEnum.EMERGENCY_DETECTED.value,
                ]
            ),
        )
        .order_by(SessionEvent.occurred_at)
    )
    events = (await db.execute(stmt)).all()
    disconnected_at: dict[UUID, datetime] = {}
    disconnections: dict[UUID, list[BackofficeSessionDisconnectionDTO]] = {}
    emergency_detections: dict[UUID, list[datetime]] = {}

    for session_id, kind, occurred_at in events:
        if kind == SessionEventKindEnum.EMERGENCY_DETECTED.value:
            emergency_detections.setdefault(session_id, []).append(occurred_at)
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

    items = []

    for session in sessions:
        parrot_count, mimicry_count = sound_counts.get(session.id, (0, 0))

        items.append(
            BackofficeSessionDTO(
                **build_session_dto(session, judgment_statuses[session.id]).model_dump(exclude={"word", "period"}),
                word=BackofficeSessionWordDTO(id=session.word_id, name=word_names[session.word_id]),
                period=BackofficeSessionPeriodDTO(
                    started_at=session.started_at,
                    ended_at=session.ended_at,
                    ended_by=session.ended_by,
                    ended_reason=session.ended_reason,
                ),
                sounds=BackofficeSessionSoundsDTO(parrot_count=parrot_count, mimicry_count=mimicry_count),
                disconnections=disconnections.get(session.id, []),
                emergency_detections=emergency_detections.get(session.id, []),
            )
        )

    return items, total


async def get_detail(*, db: AsyncSession, session: Session) -> SessionDTO:
    judgment_statuses = await get_judgment_statuses(db=db, sessions=[session])

    return build_session_dto(session, judgment_statuses[session.id])


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

    return build_session_dto(session, JudgmentStatusEnum.PENDING)


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

    await db.flush()

    judgment_statuses = await get_judgment_statuses(db=db, sessions=[session])

    return build_session_dto(session, judgment_statuses[session.id])


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

    await db.flush()

    return [session.id for session in sessions]


@transactional(unavailable_error=SessionSaveUnavailableError)
async def backfill_ended_reasons(*, db: AsyncSession) -> None:
    await db.execute(
        update(Session)
        .where(Session.status == SessionStatusEnum.FINISHED.value, Session.ended_reason.is_(None))
        .values(
            ended_reason=case(
                (Session.ended_by == SessionActorEnum.USER.value, SessionEndReasonEnum.USER.value),
                (
                    Session.ended_at == func.coalesce(Session.last_heartbeat_at, Session.started_at),
                    SessionEndReasonEnum.HEARTBEAT_EXPIRED.value,
                ),
                (Session.ended_at == Session.scheduled_end_at, SessionEndReasonEnum.SCHEDULED.value),
                else_=SessionEndReasonEnum.DEVICE_RELEASED.value,
            )
        )
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def record_heartbeat(
    *, db: AsyncSession, session: Session, device: Device, data: HeartbeatRequest
) -> HeartbeatDTO:
    verify_station(session, device)
    verify_running(session)

    now = datetime.now(UTC)
    session.current_phase = data.current_phase.value if data.current_phase is not None else None
    session.phase_started_at = data.phase_started_at
    session.last_heartbeat_at = now
    device.last_seen_at = now

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


async def get_events(*, db: AsyncSession, session: Session) -> list[SessionEventDTO]:
    stmt = (
        select(SessionEvent)
        .where(
            SessionEvent.session_id == session.id,
            SessionEvent.kind != SessionEventKindEnum.EMERGENCY_DETECTED.value,
        )
        .order_by(SessionEvent.occurred_at)
    )
    events = (await db.scalars(stmt)).all()

    return [
        SessionEventDTO(
            id=event.id,
            kind=event.kind,
            occurred_at=event.occurred_at,
            word=SessionEventWordDTO(id=event.word_id) if event.word_id is not None else None,
        )
        for event in events
    ]


async def get_backoffice_events(*, db: AsyncSession, session: Session) -> list[BackofficeSessionEventDTO]:
    stmt = (
        select(SessionEvent, Word.name)
        .outerjoin(Word, Word.id == SessionEvent.word_id)
        .where(SessionEvent.session_id == session.id)
        .order_by(SessionEvent.occurred_at)
        .execution_options(include_deleted=True)
    )
    rows = (await db.execute(stmt)).all()
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
                word=BackofficeSessionWordDTO(id=event.word_id, name=word_name) if event.word_id is not None else None,
                is_learning=is_learning,
            )
        )

    return items


async def get_summary(*, db: AsyncSession, session: Session) -> SessionSummaryDTO:
    stmt = select(Word).where(Word.id == session.word_id).execution_options(include_deleted=True)
    word = await db.scalar(stmt)

    stmt = select(func.sum(LearningSegment.play_count)).where(LearningSegment.session_id == session.id)
    play_count = await db.scalar(stmt)

    stmt = select(Session).where(Session.user_id == session.user_id)
    user_sessions = (await db.scalars(stmt)).all()
    active_periods = await get_active_periods(db=db, sessions=user_sessions)
    durations = {
        user_session.id: sum(
            (ended_at - started_at for started_at, ended_at in active_periods[user_session.id]), timedelta(0)
        )
        // timedelta(milliseconds=1)
        for user_session in user_sessions
    }
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
