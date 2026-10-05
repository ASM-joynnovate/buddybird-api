from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid7

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.db import transactional
from app.enums import FileStatusEnum
from app.errors import (
    FileSizeExceededError,
    InvalidWordRecordingError,
    ResourceNotFoundError,
    WordRecordingRequiredError,
    WordSaveUnavailableError,
)
from app.models import File, User, Word, WordRecording
from app.s3 import UPLOAD_URL_EXPIRES_IN, S3StorageClient
from app.schemas.base import FileDTO
from app.schemas.words import (
    SaveWordRequest,
    WordDTO,
    WordRecordingDTO,
    WordRecordingUploadDTO,
    WordRecordingUploadRequest,
)

MAX_RECORDING_BYTES = 5 * 1024 * 1024
RECORDING_TYPES = {
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/m4a": "m4a",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
}


def build_word_dto(word: Word, recordings: Iterable[WordRecording], storage: S3StorageClient) -> WordDTO:
    return WordDTO(
        id=word.id,
        name=word.name,
        recordings=[
            WordRecordingDTO(
                id=recording.id,
                audio_file=FileDTO(
                    url=storage.generate_presigned_url(path=recording.file.object_key),
                    status=recording.file.status,
                ),
                display_order=recording.display_order,
                created_at=recording.created_at,
            )
            for recording in recordings
        ],
    )


async def get_recordings_by_word(*, db: AsyncSession, word_ids: Iterable[UUID]) -> dict[UUID, list[WordRecording]]:
    stmt = (
        select(WordRecording)
        .join(File, File.id == WordRecording.file_id)
        .options(contains_eager(WordRecording.file))
        .where(
            WordRecording.word_id.in_(word_ids),
            or_(
                File.status == FileStatusEnum.UPLOADED.value,
                and_(
                    File.status == FileStatusEnum.PENDING.value,
                    File.created_at > datetime.now(UTC) - timedelta(seconds=UPLOAD_URL_EXPIRES_IN),
                ),
            ),
        )
        .order_by(WordRecording.display_order, WordRecording.created_at)
    )
    recordings = (await db.scalars(stmt)).all()
    grouped: dict[UUID, list[WordRecording]] = {}

    for recording in recordings:
        grouped.setdefault(recording.word_id, []).append(recording)

    return grouped


async def get_list(*, db: AsyncSession, user: User, storage: S3StorageClient) -> list[WordDTO]:
    words = (await db.scalars(select(Word).where(Word.user_id == user.id).order_by(Word.created_at))).all()
    recordings = await get_recordings_by_word(db=db, word_ids=[word.id for word in words])

    return [build_word_dto(word, recordings.get(word.id, []), storage) for word in words]


@transactional(unavailable_error=WordSaveUnavailableError)
async def create(*, db: AsyncSession, user: User, storage: S3StorageClient, data: SaveWordRequest) -> WordDTO:
    word = Word(user_id=user.id, name=data.name, is_deleted=False)

    db.add(word)
    await db.flush()

    return build_word_dto(word, [], storage)


@transactional(unavailable_error=WordSaveUnavailableError)
async def update(*, db: AsyncSession, storage: S3StorageClient, word: Word, data: SaveWordRequest) -> WordDTO:
    word.name = data.name

    await db.flush()

    recordings = await get_recordings_by_word(db=db, word_ids=[word.id])

    return build_word_dto(word, recordings.get(word.id, []), storage)


@transactional(unavailable_error=WordSaveUnavailableError)
async def delete(*, db: AsyncSession, word: Word) -> None:
    recordings = [
        recording
        for recording in (await get_recordings_by_word(db=db, word_ids=[word.id])).get(word.id, [])
        if recording.file.status == FileStatusEnum.UPLOADED.value
    ]

    word.is_deleted = True

    for recording in recordings:
        recording.is_deleted = True

        if recording.file.file_path.startswith(f"user/{word.user_id}/"):
            recording.file.is_deleted = True

    await db.flush()


@transactional(unavailable_error=WordSaveUnavailableError)
async def add_recording(
    *, db: AsyncSession, storage: S3StorageClient, word: Word, data: WordRecordingUploadRequest
) -> WordRecordingUploadDTO:
    extension = RECORDING_TYPES.get(data.content_type)

    if extension is None:
        raise InvalidWordRecordingError

    if data.file_size > MAX_RECORDING_BYTES:
        raise FileSizeExceededError

    display_order = data.display_order

    if display_order is None:
        stmt = select(func.coalesce(func.max(WordRecording.display_order) + 1, 0)).where(
            WordRecording.word_id == word.id
        )
        display_order = await db.scalar(stmt)

    file_id = uuid7()
    file_path = f"user/{word.user_id}/word/{word.id}/{file_id}"
    file_name = f"recording.{extension}"

    recording_file = File(
        id=file_id,
        file_name=file_name,
        file_path=file_path,
        file_size=data.file_size,
        file_type=data.content_type,
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )

    recording = WordRecording(word_id=word.id, file=recording_file, display_order=display_order, is_deleted=False)

    db.add(recording_file)
    db.add(recording)

    await db.flush()

    upload = storage.generate_presigned_upload(
        file_id=file_id,
        path=recording_file.object_key,
        content_type=data.content_type,
        file_size=data.file_size,
    )

    return WordRecordingUploadDTO(**upload.model_dump(), recording_id=recording.id)


@transactional(unavailable_error=WordSaveUnavailableError)
async def delete_recording(*, db: AsyncSession, word: Word, recording_id: UUID) -> None:
    recordings = [
        recording
        for recording in (await get_recordings_by_word(db=db, word_ids=[word.id])).get(word.id, [])
        if recording.file.status == FileStatusEnum.UPLOADED.value
    ]
    recording = next((item for item in recordings if item.id == recording_id), None)

    if recording is None:
        raise ResourceNotFoundError

    if len(recordings) <= 1:
        raise WordRecordingRequiredError

    recording.is_deleted = True

    if recording.file.file_path.startswith(f"user/{word.user_id}/"):
        recording.file.is_deleted = True

    await db.flush()


async def get_detail(*, db: AsyncSession, storage: S3StorageClient, word: Word) -> WordDTO:
    recordings = await get_recordings_by_word(db=db, word_ids=[word.id])

    return build_word_dto(word, recordings.get(word.id, []), storage)
