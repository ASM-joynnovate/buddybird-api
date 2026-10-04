import logging
from uuid import uuid7

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import FileStatusEnum, PresetLanguageEnum
from app.errors import (
    DuplicatePresetWordError,
    FileSizeExceededError,
    InvalidWordRecordingError,
    PresetWordSaveUnavailableError,
)
from app.models import File, PresetWord
from app.s3 import S3StorageClient
from app.schemas.base import FileDTO
from app.schemas.preset_words import CreatePresetWordRequest, PresetWordDTO, UpdatePresetWordRequest
from app.services.words import MAX_RECORDING_BYTES, RECORDING_TYPES

logger = logging.getLogger(__name__)


def build_preset_word_dto(preset_word: PresetWord, storage: S3StorageClient) -> PresetWordDTO:
    return PresetWordDTO(
        id=preset_word.id,
        language=PresetLanguageEnum(preset_word.language),
        name=preset_word.name,
        audio_file=FileDTO(
            url=storage.generate_presigned_url(path=preset_word.audio_file.object_key),
            status=FileStatusEnum(preset_word.audio_file.status),
        ),
    )


async def get_list(*, db: AsyncSession, storage: S3StorageClient) -> list[PresetWordDTO]:
    stmt = select(PresetWord).order_by(PresetWord.language, PresetWord.created_at)
    preset_words = (await db.scalars(stmt)).all()

    return [build_preset_word_dto(preset_word, storage) for preset_word in preset_words]


@transactional(unavailable_error=PresetWordSaveUnavailableError)
async def save_preset_word(*, db: AsyncSession, preset_word: PresetWord) -> None:
    db.add(preset_word)

    try:
        await db.flush()
    except IntegrityError as exc:
        raise DuplicatePresetWordError from exc


async def create(*, db: AsyncSession, storage: S3StorageClient, data: CreatePresetWordRequest) -> PresetWordDTO:
    preset_word = PresetWord(language=data.language, is_deleted=False)

    return await update(db=db, storage=storage, preset_word=preset_word, data=data)


async def update(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    preset_word: PresetWord,
    data: CreatePresetWordRequest | UpdatePresetWordRequest,
) -> PresetWordDTO:
    audio_file = None

    if data.file is not None:
        content_type = data.file.content_type

        if content_type is None or content_type not in RECORDING_TYPES:
            raise InvalidWordRecordingError

        content = await data.file.read()

        if len(content) > MAX_RECORDING_BYTES:
            raise FileSizeExceededError

        file_id = uuid7()

        audio_file = File(
            id=file_id,
            file_name=f"recording.{RECORDING_TYPES[content_type]}",
            file_path=f"preset/{file_id}",
            file_size=len(content),
            file_type=content_type,
            is_deleted=False,
            status=FileStatusEnum.UPLOADED.value,
        )

        await storage.upload(path=audio_file.object_key, file=content, content_type=content_type)

        preset_word.audio_file = audio_file

    if data.name is not None:
        preset_word.name = data.name

    try:
        await save_preset_word(db=db, preset_word=preset_word)
    except Exception:
        if audio_file is not None:
            try:
                await storage.delete(path=audio_file.object_key)
            except BotoCoreError, ClientError:
                logger.exception("업로드된 프리셋 오디오 정리 실패")

        raise

    return build_preset_word_dto(preset_word, storage)


@transactional(unavailable_error=PresetWordSaveUnavailableError)
async def delete(*, db: AsyncSession, preset_word: PresetWord) -> None:
    preset_word.is_deleted = True

    await db.flush()
