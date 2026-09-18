import asyncio
from collections.abc import Sequence
from datetime import datetime
from uuid import uuid7

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import FileSizeExceededError, InvalidSessionSoundError, SessionSaveUnavailableError
from app.models import Device, File, Session, SessionSound, SoundJudgment, User
from app.s3 import S3StorageClient
from app.schemas.base import PageParams
from app.schemas.sessions import SessionSoundAudioDTO, SessionSoundDTO, SessionSoundJudgmentDTO
from app.services.sessions import verify_station
from app.services.users import delete_uploaded_photo

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
            audio=SessionSoundAudioDTO(url=storage.generate_presigned_url(path=sound.audio_file.object_key)),
            judgment=SessionSoundJudgmentDTO(word_id=judgments[sound.id]) if sound.id in judgments else None,
        )
        for sound in sounds
    ]


async def get_list(
    *, db: AsyncSession, storage: S3StorageClient, session: Session, query: PageParams
) -> tuple[list[SessionSoundDTO], int]:
    stmt = select(SessionSound).where(SessionSound.session_id == session.id, SessionSound.is_parrot_sound.is_not(False))
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    sounds = (
        await db.scalars(
            stmt.order_by(SessionSound.captured_at.desc())
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
        .where(Session.user_id == user.id, SessionSound.is_parrot_sound.is_not(False))
    )
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    sounds = (
        await db.scalars(
            stmt.order_by(SessionSound.captured_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return await build_sound_dtos(db=db, storage=storage, sounds=sounds), total


async def upload(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    session: Session,
    device: Device,
    file: UploadFile,
    captured_at: datetime,
) -> SessionSoundDTO:
    verify_station(session, device)

    file_type = (file.content_type or "").partition(";")[0].lower()

    if file_type not in SOUND_TYPES:
        raise InvalidSessionSoundError

    content = await file.read(MAX_SOUND_BYTES + 1)

    if len(content) > MAX_SOUND_BYTES:
        raise FileSizeExceededError

    if not content:
        raise InvalidSessionSoundError

    file_id = uuid7()
    file_path = f"user/{session.user_id}/session/{session.id}/sound/{file_id}"
    path = f"{file_path}/sound.wav"

    try:
        version_id = await storage.upload(path=path, file=content)
    except (BotoCoreError, ClientError, OSError, TimeoutError) as exc:
        raise SessionSaveUnavailableError from exc

    audio_file = File(
        id=file_id,
        file_name="sound.wav",
        file_path=file_path,
        file_size=len(content),
        file_type=file_type,
        is_deleted=False,
    )
    sound = SessionSound(session_id=session.id, captured_at=captured_at, audio_file=audio_file, is_deleted=False)

    try:
        await save_sound(db=db, audio_file=audio_file, sound=sound)
    except Exception, asyncio.CancelledError:
        await delete_uploaded_photo(storage=storage, path=path, version_id=version_id)

        raise

    return SessionSoundDTO(
        id=sound.id,
        captured_at=sound.captured_at,
        audio=SessionSoundAudioDTO(url=storage.generate_presigned_url(path=audio_file.object_key)),
        judgment=None,
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def save_sound(*, db: AsyncSession, audio_file: File, sound: SessionSound) -> None:
    db.add(audio_file)
    db.add(sound)

    await db.flush()
