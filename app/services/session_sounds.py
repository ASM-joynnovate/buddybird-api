from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid7

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.db import transactional
from app.enums import FileStatusEnum, SessionEventKindEnum, SoundJudgmentStatusEnum
from app.errors import FileSizeExceededError, InvalidSessionSoundError, SessionSaveUnavailableError
from app.models import (
    Device,
    File,
    Session,
    SessionEvent,
    SessionEventSound,
    SessionSound,
    SoundAnalysis,
    SoundJudgment,
    User,
)
from app.s3 import UPLOAD_URL_EXPIRES_IN, S3StorageClient
from app.schemas.base import FileDTO, PageParams, UploadDTO
from app.schemas.sessions import (
    BackofficeSessionSoundDTO,
    SessionSoundDTO,
    SessionSoundJudgmentDTO,
    SessionSoundListParams,
    SessionSoundUploadRequest,
)
from app.services.sessions import LATEST_JUDGED_WORD_ID, verify_station

MAX_SOUND_BYTES = 5 * 1024 * 1024
SOUND_TYPES = {"audio/wav", "audio/x-wav"}


async def build_sound_dtos(
    *, db: AsyncSession, storage: S3StorageClient, sounds: Sequence[SessionSound]
) -> list[SessionSoundDTO]:
    judgments = dict(
        (
            await db.execute(
                select(SoundJudgment.sound_id, SoundJudgment.word_id)
                .distinct(SoundJudgment.sound_id)
                .where(SoundJudgment.sound_id.in_([sound.id for sound in sounds]))
                .order_by(SoundJudgment.sound_id, SoundJudgment.judged_at.desc())
            )
        ).all()
    )

    return [
        SessionSoundDTO(
            id=sound.id,
            session_id=sound.session_id,
            captured_at=sound.captured_at,
            audio_file=FileDTO(
                url=storage.generate_presigned_url(path=sound.audio_file.object_key),
                status=sound.audio_file.status,
            ),
            judgment=SessionSoundJudgmentDTO(word_id=judgments[sound.id]) if sound.id in judgments else None,
        )
        for sound in sounds
    ]


async def get_list(
    *, db: AsyncSession, storage: S3StorageClient, session: Session, query: SessionSoundListParams
) -> tuple[list[SessionSoundDTO], int]:
    stmt = (
        select(SessionSound)
        .join(File, File.id == SessionSound.audio_file_id)
        .where(
            SessionSound.session_id == session.id,
            SessionSound.is_parrot_sound.is_not(False),
            SessionSound.judgment_status != SoundJudgmentStatusEnum.FAILED.value,
            or_(
                File.status == FileStatusEnum.UPLOADED.value,
                and_(
                    File.status == FileStatusEnum.PENDING.value,
                    File.created_at > datetime.now(UTC) - timedelta(seconds=UPLOAD_URL_EXPIRES_IN),
                ),
            ),
        )
    )

    if query.mimicry:
        stmt = stmt.where(LATEST_JUDGED_WORD_ID.is_not(None))

    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    sounds = (
        await db.scalars(
            stmt.options(contains_eager(SessionSound.audio_file))
            .order_by(SessionSound.captured_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return await build_sound_dtos(db=db, storage=storage, sounds=sounds), total


async def get_user_list(
    *, db: AsyncSession, storage: S3StorageClient, user: User, query: PageParams
) -> tuple[list[SessionSoundDTO], int]:
    stmt = (
        select(SessionSound)
        .join(Session, Session.id == SessionSound.session_id)
        .join(File, File.id == SessionSound.audio_file_id)
        .where(
            Session.user_id == user.id,
            SessionSound.is_parrot_sound.is_not(False),
            SessionSound.judgment_status != SoundJudgmentStatusEnum.FAILED.value,
            File.status == FileStatusEnum.UPLOADED.value,
        )
    )
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    sounds = (
        await db.scalars(
            stmt.options(contains_eager(SessionSound.audio_file))
            .order_by(SessionSound.captured_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return await build_sound_dtos(db=db, storage=storage, sounds=sounds), total


async def get_backoffice_list(*, db: AsyncSession, session: Session) -> list[BackofficeSessionSoundDTO]:
    stmt = (
        select(SessionSound.captured_at, LATEST_JUDGED_WORD_ID.is_not(None))
        .where(SessionSound.session_id == session.id, SessionSound.is_parrot_sound.is_(True))
        .order_by(SessionSound.captured_at)
    )
    rows = (await db.execute(stmt)).all()

    return [
        BackofficeSessionSoundDTO(captured_at=captured_at, is_mimicry=is_mimicry) for captured_at, is_mimicry in rows
    ]


@transactional(unavailable_error=SessionSaveUnavailableError)
async def upload(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    session: Session,
    device: Device,
    data: SessionSoundUploadRequest,
) -> UploadDTO:
    verify_station(session, device)

    if data.content_type not in SOUND_TYPES:
        raise InvalidSessionSoundError

    if data.file_size > MAX_SOUND_BYTES:
        raise FileSizeExceededError

    file_id = uuid7()
    file_path = f"user/{session.user_id}/session/{session.id}/sound/{file_id}"

    audio_file = File(
        id=file_id,
        file_name="sound.wav",
        file_path=file_path,
        file_size=data.file_size,
        file_type=data.content_type,
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )

    db.add(audio_file)
    db.add(
        SessionSound(
            session_id=session.id,
            captured_at=data.captured_at,
            audio_file=audio_file,
            is_deleted=False,
        )
    )

    await db.flush()

    return storage.generate_presigned_upload(
        file_id=file_id,
        path=audio_file.object_key,
        content_type=data.content_type,
        file_size=data.file_size,
    )


async def detect_emergency(*, db: AsyncSession, session_id: UUID, captured_at: datetime) -> None:
    window_size = timedelta(seconds=30)
    latest_chirp_count = (
        select(SoundAnalysis.chirp_count)
        .where(SoundAnalysis.sound_id == SessionSound.id)
        .order_by(SoundAnalysis.analyzed_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    stmt = (
        select(SessionSound.id, SessionSound.captured_at, func.coalesce(latest_chirp_count, 0).label("chirp_count"))
        .join(File, File.id == SessionSound.audio_file_id)
        .where(
            SessionSound.session_id == session_id,
            SessionSound.captured_at.between(captured_at - window_size, captured_at + window_size),
            File.status == FileStatusEnum.UPLOADED.value,
        )
        .order_by(SessionSound.captured_at)
    )
    sounds = (await db.execute(stmt)).all()

    windows = [
        [sound for sound in sounds if end.captured_at - window_size <= sound.captured_at <= end.captured_at]
        for end in sounds
        if end.captured_at >= captured_at
    ]
    emergencies = [window for window in windows if sum(sound.chirp_count for sound in window) >= 7]

    if not emergencies:
        return

    started_at = emergencies[0][0].captured_at
    ended_at = emergencies[-1][-1].captured_at
    sound_ids = {sound.id for sound in sounds if started_at <= sound.captured_at <= ended_at}

    stmt = (
        select(SessionEvent)
        .join(SessionEventSound, SessionEventSound.event_id == SessionEvent.id)
        .join(SessionSound, SessionSound.id == SessionEventSound.sound_id)
        .where(
            SessionEvent.session_id == session_id,
            SessionEvent.kind == SessionEventKindEnum.EMERGENCY_DETECTED.value,
            SessionEvent.occurred_at <= ended_at,
            SessionSound.captured_at >= started_at,
        )
        .distinct()
        .order_by(SessionEvent.occurred_at)
    )
    events = (await db.scalars(stmt)).all()

    if events:
        event = events[0]

        event.occurred_at = min(event.occurred_at, started_at)
    else:
        event = SessionEvent(
            session_id=session_id,
            kind=SessionEventKindEnum.EMERGENCY_DETECTED.value,
            occurred_at=started_at,
        )

        db.add(event)

        await db.flush()

    for merged in events[1:]:
        stmt = select(SessionEventSound.sound_id).where(SessionEventSound.event_id == merged.id)
        sound_ids.update((await db.scalars(stmt)).all())

        await db.execute(delete(SessionEventSound).where(SessionEventSound.event_id == merged.id))

        await db.delete(merged)

    await db.execute(
        insert(SessionEventSound)
        .values([{"event_id": event.id, "sound_id": sound_id} for sound_id in sound_ids])
        .on_conflict_do_nothing()
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def save_parrot_detection(
    *, db: AsyncSession, analyzer_version: str, analyzed_at: datetime, data: list[dict]
) -> list[UUID]:
    session_ids = set()

    for item in data:
        sound_id = UUID(item["audio_id"])

        stmt = (
            select(Session.id)
            .join(SessionSound, SessionSound.session_id == Session.id)
            .where(SessionSound.id == sound_id)
            .with_for_update(of=Session, key_share=True)
        )
        await db.execute(stmt)

        await db.execute(
            insert(SoundAnalysis)
            .values(
                sound_id=sound_id,
                analyzer_version=analyzer_version,
                is_parrot=item["is_parrot"],
                score=item["score"],
                call_count=item["call_count"],
                chirp_count=item["chirp_count"],
                analyzed_at=analyzed_at,
            )
            .on_conflict_do_nothing(index_elements=[SoundAnalysis.sound_id, SoundAnalysis.analyzer_version])
        )

        latest_is_parrot = (
            select(SoundAnalysis.is_parrot)
            .where(SoundAnalysis.sound_id == sound_id)
            .order_by(SoundAnalysis.analyzed_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        sound = (
            await db.execute(
                update(SessionSound)
                .where(SessionSound.id == sound_id)
                .values(is_parrot_sound=latest_is_parrot, judgment_status=SoundJudgmentStatusEnum.DONE.value)
                .returning(SessionSound.session_id, SessionSound.captured_at)
            )
        ).one()

        await detect_emergency(db=db, session_id=sound.session_id, captured_at=sound.captured_at)

        session_ids.add(sound.session_id)

    return list(session_ids)


@transactional(unavailable_error=SessionSaveUnavailableError)
async def mark_parrot_detection_failed(*, db: AsyncSession, data: list[dict]) -> None:
    await db.execute(
        update(SessionSound)
        .where(
            SessionSound.id.in_([UUID(item["audio_id"]) for item in data]),
            SessionSound.judgment_status == SoundJudgmentStatusEnum.PENDING.value,
        )
        .values(judgment_status=SoundJudgmentStatusEnum.FAILED.value)
    )
