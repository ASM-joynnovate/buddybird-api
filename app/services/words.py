from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid7

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import FileStatusEnum
from app.errors import (
    FileSizeExceededError,
    InvalidWordRecordingError,
    ResourceNotFoundError,
    WordRecordingLimitError,
    WordRecordingRequiredError,
    WordSaveUnavailableError,
)
from app.models import File, User, Word, WordRecording
from app.s3 import UPLOAD_URL_EXPIRES_IN, S3StorageClient
from app.schemas.base import UploadDTO, UploadRequest
from app.schemas.words import SaveWordRequest, WordDTO, WordRecordingDTO

MAX_RECORDING_BYTES = 5 * 1024 * 1024
MAX_RECORDINGS_PER_WORD = 5
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
                url=storage.generate_presigned_url(path=recording.file.object_key),
                created_at=recording.created_at,
            )
            for recording in recordings
        ],
    )


async def get_recordings_by_word(*, db: AsyncSession, word_ids: Iterable[UUID]) -> dict[UUID, list[WordRecording]]:
    stmt = (
        select(WordRecording)
        .join(File, File.id == WordRecording.file_id)
        .where(WordRecording.word_id.in_(word_ids), File.status == FileStatusEnum.UPLOADED.value)
        .order_by(WordRecording.created_at)
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
    recordings = await get_recordings_by_word(db=db, word_ids=[word.id])

    word.is_deleted = True

    for recording in recordings.get(word.id, []):
        recording.is_deleted = True

        if recording.file.file_path.startswith(f"user/{word.user_id}/"):
            recording.file.is_deleted = True

    await db.flush()


@transactional(unavailable_error=WordSaveUnavailableError)
async def add_recording(*, db: AsyncSession, storage: S3StorageClient, word: Word, data: UploadRequest) -> UploadDTO:
    extension = RECORDING_TYPES.get(data.content_type)

    if extension is None:
        raise InvalidWordRecordingError

    if data.file_size > MAX_RECORDING_BYTES:
        raise FileSizeExceededError

    stmt = (
        select(WordRecording)
        .join(File, File.id == WordRecording.file_id)
        .where(
            WordRecording.word_id == word.id,
            or_(
                File.status == FileStatusEnum.UPLOADED.value,
                and_(
                    File.status == FileStatusEnum.PENDING.value,
                    File.created_at > datetime.now(UTC) - timedelta(seconds=UPLOAD_URL_EXPIRES_IN),
                ),
            ),
        )
    )
    count = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))

    if count >= MAX_RECORDINGS_PER_WORD:
        raise WordRecordingLimitError

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

    db.add(recording_file)
    db.add(WordRecording(word_id=word.id, file=recording_file, is_deleted=False))

    await db.flush()

    return UploadDTO(
        file_id=file_id,
        url=storage.generate_presigned_upload_url(
            path=recording_file.object_key,
            file_type=data.content_type,
            file_size=data.file_size,
        ),
        headers={"Content-Type": data.content_type},
        expires_in=UPLOAD_URL_EXPIRES_IN,
    )


@transactional(unavailable_error=WordSaveUnavailableError)
async def delete_recording(*, db: AsyncSession, word: Word, recording_id: UUID) -> None:
    recordings = (await get_recordings_by_word(db=db, word_ids=[word.id])).get(word.id, [])
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
