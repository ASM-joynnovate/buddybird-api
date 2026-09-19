import asyncio
import logging
from pathlib import Path
from uuid import UUID, uuid7

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_or_404, transactional
from app.errors import FileSizeExceededError
from app.legacy import audio
from app.legacy.errors import InvalidAudioSegmentRangeError, InvalidLabelCategoryTargetError
from app.legacy.models import AudioCapture, AudioSegment, LabelCategory, LabelCategoryTargetEnum, LabelOption
from app.legacy.schemas.segments import (
    AssignAudioSegmentLabelRequest,
    CreateAudioSegmentRequest,
    TrimAudioSegmentRequest,
    UpdateAudioSegmentMemoRequest,
)
from app.models import File
from app.s3 import S3StorageClient

logger = logging.getLogger(__name__)


def _create_audio_file(*, name: str, path: str, content: bytes) -> File:
    size = len(content)

    if size > 1024**2:
        value = size / 1024.0**2
        unit = "MB"

        for next_unit in ("GB", "TB", "PB"):
            if value < 1024:
                break

            value /= 1024
            unit = next_unit

        size_text = f"{int(value)}{unit}" if value.is_integer() else f"{value:.1f}{unit}"

        raise FileSizeExceededError(
            message=f"최대 파일 크기를 초과했습니다. 현재 파일 크기: {size_text}, 최대 크기: 1MB"
        )

    file_id = uuid7()

    return File(
        id=file_id,
        file_name=Path(name).name,
        file_path=f"{path}/{file_id}",
        file_size=len(content),
        file_type="audio/wav",
        is_deleted=False,
    )


@transactional
async def save_audio_segment(
    *, db: AsyncSession, audio_capture_id: UUID, segment_id: UUID, file: File, start_ms: int, end_ms: int
) -> None:
    db.add(
        AudioSegment(
            id=segment_id,
            audio_capture_id=audio_capture_id,
            start_ms=start_ms,
            end_ms=end_ms,
            audio_file=file,
            label_option_id=None,
            memo=None,
            is_deleted=False,
        )
    )


@transactional
async def replace_audio_segment_file(
    *, db: AsyncSession, audio_segment_id: UUID, file: File, start_ms: int, end_ms: int
) -> None:
    segment = await get_or_404(db=db, model=AudioSegment, id=audio_segment_id)
    old_file = segment.audio_file

    segment.audio_file = file
    segment.start_ms = start_ms
    segment.end_ms = end_ms
    old_file.is_deleted = True


async def create_audio_segment(
    *, db: AsyncSession, storage: S3StorageClient, audio_capture_id: UUID, data: CreateAudioSegmentRequest
) -> None:
    capture = await get_or_404(db=db, model=AudioCapture, id=audio_capture_id)

    if data.end_ms <= data.start_ms:
        raise InvalidAudioSegmentRangeError

    source = await storage.download(path=capture.audio_file.object_key)
    content = await asyncio.to_thread(audio.trim, file=source, start_ms=data.start_ms, end_ms=data.end_ms)

    segment_id = uuid7()
    file = _create_audio_file(
        name=capture.audio_file.file_name,
        path=f"audio_capture/{capture.firebase_anon_uid}/{capture.id}/segments/{segment_id}",
        content=content,
    )

    await storage.upload(path=file.object_key, file=content)

    try:
        await save_audio_segment(
            db=db,
            audio_capture_id=capture.id,
            segment_id=segment_id,
            file=file,
            start_ms=data.start_ms,
            end_ms=data.end_ms,
        )
    except Exception:
        try:
            await storage.delete(path=file.object_key)
        except Exception:
            logger.exception("업로드된 오디오 파일 정리 실패")

        raise


async def trim_audio_segment(
    *, db: AsyncSession, storage: S3StorageClient, audio_segment_id: UUID, data: TrimAudioSegmentRequest
) -> None:
    segment = await get_or_404(db=db, model=AudioSegment, id=audio_segment_id)
    capture = await get_or_404(db=db, model=AudioCapture, id=segment.audio_capture_id)

    if data.end_ms <= data.start_ms:
        raise InvalidAudioSegmentRangeError

    source = await storage.download(path=capture.audio_file.object_key)
    content = await asyncio.to_thread(audio.trim, file=source, start_ms=data.start_ms, end_ms=data.end_ms)

    old_file = segment.audio_file
    file = _create_audio_file(name=old_file.file_name, path=old_file.file_path.rsplit("/", 1)[0], content=content)

    await storage.upload(path=file.object_key, file=content)

    try:
        await replace_audio_segment_file(
            db=db,
            audio_segment_id=segment.id,
            file=file,
            start_ms=data.start_ms,
            end_ms=data.end_ms,
        )
    except Exception:
        try:
            await storage.delete(path=file.object_key)
        except Exception:
            logger.exception("업로드된 오디오 파일 정리 실패")

        raise


@transactional
async def delete_audio_segment(*, db: AsyncSession, audio_segment_id: UUID) -> None:
    segment = await get_or_404(db=db, model=AudioSegment, id=audio_segment_id)

    segment.audio_file.is_deleted = True
    segment.is_deleted = True


@transactional
async def assign_audio_segment_label(
    *, db: AsyncSession, audio_segment_id: UUID, data: AssignAudioSegmentLabelRequest
) -> None:
    segment = await get_or_404(db=db, model=AudioSegment, id=audio_segment_id)
    option = await get_or_404(db=db, model=LabelOption, id=data.label_option_id)
    category = await get_or_404(db=db, model=LabelCategory, id=option.category_id)

    if category.target != LabelCategoryTargetEnum.SEGMENT:
        raise InvalidLabelCategoryTargetError

    segment.label_option_id = option.id


@transactional
async def update_audio_segment_memo(
    *, db: AsyncSession, audio_segment_id: UUID, data: UpdateAudioSegmentMemoRequest
) -> None:
    segment = await get_or_404(db=db, model=AudioSegment, id=audio_segment_id)

    segment.memo = data.memo
