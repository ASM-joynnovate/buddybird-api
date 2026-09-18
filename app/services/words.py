import asyncio
from collections.abc import Iterable
from uuid import UUID, uuid7

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import (
    FileSizeExceededError,
    InvalidWordRecordingError,
    ResourceNotFoundError,
    WordRecordingLimitError,
    WordRecordingRequiredError,
    WordSaveUnavailableError,
)
from app.models import File, User, Word, WordRecording
from app.s3 import S3StorageClient
from app.schemas.words import SaveWordRequest, WordDTO, WordRecordingDTO
from app.services.users import delete_uploaded_photo

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
    recordings = (
        await db.scalars(
            select(WordRecording).where(WordRecording.word_id.in_(word_ids)).order_by(WordRecording.created_at)
        )
    ).all()
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


async def add_recording(*, db: AsyncSession, storage: S3StorageClient, word: Word, file: UploadFile) -> WordDTO:
    recordings = await get_recordings_by_word(db=db, word_ids=[word.id])

    if len(recordings.get(word.id, [])) >= MAX_RECORDINGS_PER_WORD:
        raise WordRecordingLimitError

    file_type = (file.content_type or "").partition(";")[0].lower()
    extension = RECORDING_TYPES.get(file_type)

    if extension is None:
        raise InvalidWordRecordingError

    content = await file.read(MAX_RECORDING_BYTES + 1)

    if len(content) > MAX_RECORDING_BYTES:
        raise FileSizeExceededError

    if not content:
        raise InvalidWordRecordingError

    file_id = uuid7()
    file_path = f"user/{word.user_id}/word/{word.id}/{file_id}"
    file_name = f"recording.{extension}"
    path = f"{file_path}/{file_name}"

    try:
        version_id = await storage.upload(path=path, file=content)
    except (BotoCoreError, ClientError, OSError, TimeoutError) as exc:
        raise WordSaveUnavailableError from exc

    recording_file = File(
        id=file_id,
        file_name=file_name,
        file_path=file_path,
        file_size=len(content),
        file_type=file_type,
        is_deleted=False,
    )

    try:
        await save_recording(db=db, word=word, recording_file=recording_file)
    except Exception, asyncio.CancelledError:
        await delete_uploaded_photo(storage=storage, path=path, version_id=version_id)

        raise

    recordings = await get_recordings_by_word(db=db, word_ids=[word.id])

    return build_word_dto(word, recordings.get(word.id, []), storage)


@transactional(unavailable_error=WordSaveUnavailableError)
async def save_recording(*, db: AsyncSession, word: Word, recording_file: File) -> None:
    recordings = await get_recordings_by_word(db=db, word_ids=[word.id])

    if len(recordings.get(word.id, [])) >= MAX_RECORDINGS_PER_WORD:
        raise WordRecordingLimitError

    db.add(recording_file)
    db.add(WordRecording(word_id=word.id, file=recording_file, is_deleted=False))

    await db.flush()


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
