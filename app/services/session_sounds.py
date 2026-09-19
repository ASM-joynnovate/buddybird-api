from collections.abc import Sequence
from uuid import uuid7

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import FileStatusEnum
from app.errors import FileSizeExceededError, InvalidSessionSoundError, SessionSaveUnavailableError
from app.models import Device, File, Session, SessionSound, SoundJudgment, User
from app.s3 import UPLOAD_URL_EXPIRES_IN, S3StorageClient
from app.schemas.base import PageParams, UploadDTO
from app.schemas.sessions import (
    SessionSoundAudioDTO,
    SessionSoundDTO,
    SessionSoundJudgmentDTO,
    SessionSoundUploadRequest,
)
from app.services.sessions import verify_station

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
    stmt = (
        select(SessionSound)
        .join(File, File.id == SessionSound.audio_file_id)
        .where(
            SessionSound.session_id == session.id,
            SessionSound.is_parrot_sound.is_not(False),
            File.status == FileStatusEnum.UPLOADED.value,
        )
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
            File.status == FileStatusEnum.UPLOADED.value,
        )
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

    return UploadDTO(
        file_id=file_id,
        url=storage.generate_presigned_upload_url(
            path=audio_file.object_key,
            file_type=data.content_type,
            file_size=data.file_size,
        ),
        headers={"Content-Type": data.content_type},
        expires_in=UPLOAD_URL_EXPIRES_IN,
    )
