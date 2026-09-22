from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import SessionActorEnum, SessionEventKindEnum, SessionStatusEnum
from app.errors import (
    DeviceNotStationError,
    ResourceNotFoundError,
    SessionAlreadyRunningError,
    SessionNotRunningError,
    SessionSaveUnavailableError,
)
from app.models import Device, LearningDailySummary, Session, SessionEvent, User, Word
from app.schemas.base import PageParams
from app.schemas.sessions import (
    AcknowledgedSummaryDTO,
    AddSessionEventsRequest,
    ChangeSessionLearningRequest,
    ChangeSessionWordRequest,
    HeartbeatDTO,
    HeartbeatRequest,
    HeartbeatSessionDTO,
    SessionDTO,
    SessionEventDTO,
    SessionEventWordDTO,
    SessionPeriodDTO,
    SessionProgressDTO,
    SessionSettingsDTO,
    SessionStationDTO,
    StartSessionRequest,
)


def build_session_dto(session: Session) -> SessionDTO:
    return SessionDTO(
        id=session.id,
        status=session.status,
        station=SessionStationDTO(device_id=session.station_device_id),
        settings=SessionSettingsDTO(
            word_id=session.word_id,
            learning_enabled=session.learning_enabled,
            version=session.settings_version,
            applied_version=session.applied_settings_version,
        ),
        progress=SessionProgressDTO(
            current_phase=session.current_phase,
            phase_started_at=session.phase_started_at,
            last_heartbeat_at=session.last_heartbeat_at,
        ),
        period=SessionPeriodDTO(started_at=session.started_at, ended_at=session.ended_at, ended_by=session.ended_by),
    )


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

    return [build_session_dto(session) for session in sessions], total


def get_detail(*, session: Session) -> SessionDTO:
    return build_session_dto(session)


@transactional(unavailable_error=SessionSaveUnavailableError)
async def start(*, db: AsyncSession, user: User, device: Device, data: StartSessionRequest) -> SessionDTO:
    if data.word_id is not None:
        await verify_words_owned(db=db, user_id=user.id, word_ids={data.word_id})

    now = datetime.now(UTC)
    session = Session(
        user_id=user.id,
        station_device_id=device.id,
        status=SessionStatusEnum.RUNNING.value,
        word_id=data.word_id,
        learning_enabled=data.learning_enabled,
        settings_version=1,
        applied_settings_version=0,
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

    return build_session_dto(session)


@transactional(unavailable_error=SessionSaveUnavailableError)
async def change_word(*, db: AsyncSession, session: Session, data: ChangeSessionWordRequest) -> SessionDTO:
    verify_running(session)

    if data.word_id is not None:
        await verify_words_owned(db=db, user_id=session.user_id, word_ids={data.word_id})

    session.word_id = data.word_id
    session.settings_version += 1

    db.add(
        SessionEvent(
            session_id=session.id,
            kind=SessionEventKindEnum.WORD_CHANGED.value,
            occurred_at=datetime.now(UTC),
            word_id=data.word_id,
        )
    )

    await db.flush()

    return build_session_dto(session)


@transactional(unavailable_error=SessionSaveUnavailableError)
async def change_learning(*, db: AsyncSession, session: Session, data: ChangeSessionLearningRequest) -> SessionDTO:
    verify_running(session)

    session.learning_enabled = data.enabled
    session.settings_version += 1

    db.add(
        SessionEvent(
            session_id=session.id,
            kind=SessionEventKindEnum.LEARNING_TOGGLED.value,
            occurred_at=datetime.now(UTC),
        )
    )

    await db.flush()

    return build_session_dto(session)


@transactional(unavailable_error=SessionSaveUnavailableError)
async def finish(*, db: AsyncSession, session: Session) -> SessionDTO:
    verify_running(session)

    now = datetime.now(UTC)
    session.status = SessionStatusEnum.FINISHED.value
    session.ended_at = now
    session.ended_by = SessionActorEnum.USER.value

    db.add(
        SessionEvent(
            session_id=session.id,
            kind=SessionEventKindEnum.SESSION_FINISHED.value,
            occurred_at=now,
        )
    )

    await db.flush()

    return build_session_dto(session)


@transactional(unavailable_error=SessionSaveUnavailableError)
async def record_heartbeat(
    *, db: AsyncSession, session: Session, device: Device, data: HeartbeatRequest
) -> HeartbeatDTO:
    verify_station(session, device)

    now = datetime.now(UTC)
    session.current_phase = data.current_phase.value if data.current_phase is not None else None
    session.phase_started_at = data.phase_started_at
    session.applied_settings_version = data.applied_settings_version
    session.last_heartbeat_at = now
    device.timezone = data.timezone
    device.last_seen_at = now

    summaries: dict[tuple[UUID, date], dict] = {}

    for summary in data.summaries:
        current = summaries.get((summary.word_id, summary.local_date))

        if current is None:
            summaries[(summary.word_id, summary.local_date)] = {
                "session_id": session.id,
                "word_id": summary.word_id,
                "local_date": summary.local_date,
                "play_count": summary.play_count,
                "play_duration_ms": summary.play_duration_ms,
            }
        else:
            current["play_count"] = max(current["play_count"], summary.play_count)
            current["play_duration_ms"] = max(current["play_duration_ms"], summary.play_duration_ms)

    if summaries:
        await verify_words_owned(db=db, user_id=session.user_id, word_ids={word_id for word_id, _ in summaries})

        stmt = insert(LearningDailySummary).values(list(summaries.values()))
        await db.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    LearningDailySummary.session_id,
                    LearningDailySummary.word_id,
                    LearningDailySummary.local_date,
                ],
                set_={
                    "play_count": func.greatest(LearningDailySummary.play_count, stmt.excluded.play_count),
                    "play_duration_ms": func.greatest(
                        LearningDailySummary.play_duration_ms, stmt.excluded.play_duration_ms
                    ),
                },
            )
        )

    await db.flush()

    return HeartbeatDTO(
        session=HeartbeatSessionDTO(
            status=session.status,
            settings=SessionSettingsDTO(
                word_id=session.word_id,
                learning_enabled=session.learning_enabled,
                version=session.settings_version,
                applied_version=session.applied_settings_version,
            ),
        ),
        acknowledged=[
            AcknowledgedSummaryDTO(word_id=word_id, local_date=local_date) for word_id, local_date in summaries
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
    events = (
        await db.scalars(
            select(SessionEvent).where(SessionEvent.session_id == session.id).order_by(SessionEvent.occurred_at)
        )
    ).all()

    return [
        SessionEventDTO(
            id=event.id,
            kind=event.kind,
            occurred_at=event.occurred_at,
            word=SessionEventWordDTO(id=event.word_id) if event.word_id is not None else None,
        )
        for event in events
    ]
