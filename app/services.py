import asyncio
import io
import logging
import zipfile
from collections import defaultdict
from contextlib import suppress
from pathlib import Path
from uuid import UUID, uuid7

from sqlalchemy import delete, func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app import audio
from app.db import session_factory, transactional
from app.errors import (
    AudioSegmentSaveConflictError,
    DuplicateLabelCategoryError,
    DuplicateLabelOptionError,
    DuplicateReviewAudioFileIdError,
    FileSizeExceededError,
    InvalidAudioSegmentRangeError,
    InvalidLabelCategoryTargetError,
    ResourceNotFoundError,
)
from app.models import (
    AudioCapture,
    AudioSegment,
    File,
    LabelCategory,
    LabelCategoryTargetEnum,
    LabelOption,
    Word,
    audio_capture_label_table,
)
from app.s3 import S3StorageClient
from app.schemas import (
    AssignAudioCaptureLabelsRequest,
    AssignAudioSegmentLabelRequest,
    CreateAudioSegmentRequest,
    CreateLabelCategoryRequest,
    CreateLabelOptionRequest,
    GetAudioCaptureDetailDTO,
    GetAudioCaptureDTO,
    GetAudioCaptureListItemDTO,
    GetAudioCaptureListRequest,
    GetAudioSegmentDTO,
    GetLabelCategoryDTO,
    GetLabelOptionDTO,
    MigrateReviewResultDTO,
    MigrateReviewsRequest,
    TrimAudioSegmentRequest,
    UpdateAudioCaptureMemoRequest,
    UpdateAudioSegmentMemoRequest,
    UpdateLabelCategoryRequest,
    UpdateLabelOptionRequest,
)

logger = logging.getLogger(__name__)


async def get_label_list(*, db: AsyncSession) -> list[GetLabelCategoryDTO]:
    categories = await db.scalars(select(LabelCategory).order_by(LabelCategory.display_order))

    return [
        GetLabelCategoryDTO(
            id=category.id,
            name=category.name,
            display_order=category.display_order,
            target=LabelCategoryTargetEnum(category.target),
            options=[
                GetLabelOptionDTO(id=option.id, name=option.name, display_order=option.display_order)
                for option in category.options
            ],
        )
        for category in categories
    ]


@transactional
async def create_label_category(*, db: AsyncSession, data: CreateLabelCategoryRequest) -> None:
    if await db.scalar(
        select(LabelCategory.id).where(LabelCategory.name == data.name, LabelCategory.target == data.target).limit(1)
    ):
        raise DuplicateLabelCategoryError

    db.add(
        LabelCategory(
            id=uuid7(), name=data.name, display_order=data.display_order, target=data.target, is_deleted=False
        )
    )


@transactional
async def update_label_category(*, db: AsyncSession, label_category_id: UUID, data: UpdateLabelCategoryRequest) -> None:
    category = await db.scalar(select(LabelCategory).where(LabelCategory.id == label_category_id))

    if category is None:
        raise ResourceNotFoundError

    for name, value in data.model_dump(exclude_unset=True).items():
        setattr(category, name, value)


@transactional
async def delete_label_category(*, db: AsyncSession, label_category_id: UUID) -> None:
    category = await db.scalar(select(LabelCategory).where(LabelCategory.id == label_category_id))

    if category is None:
        raise ResourceNotFoundError

    option_ids = [option.id for option in category.options]

    if option_ids:
        await db.execute(
            update(AudioSegment).where(AudioSegment.label_option_id.in_(option_ids)).values(label_option_id=None)
        )

        await db.execute(
            delete(audio_capture_label_table).where(audio_capture_label_table.c.label_option_id.in_(option_ids))
        )

    for option in category.options:
        option.is_deleted = True

    category.is_deleted = True


@transactional
async def create_label_option(*, db: AsyncSession, label_category_id: UUID, data: CreateLabelOptionRequest) -> None:
    category = await db.scalar(select(LabelCategory).where(LabelCategory.id == label_category_id))

    if category is None:
        raise ResourceNotFoundError

    if await db.scalar(
        select(LabelOption.id)
        .where(LabelOption.category_id == label_category_id, LabelOption.name == data.name)
        .limit(1)
    ):
        raise DuplicateLabelOptionError

    db.add(
        LabelOption(
            id=uuid7(),
            category_id=label_category_id,
            name=data.name,
            display_order=data.display_order,
            is_deleted=False,
        )
    )


@transactional
async def update_label_option(*, db: AsyncSession, label_option_id: UUID, data: UpdateLabelOptionRequest) -> None:
    option = await db.scalar(select(LabelOption).where(LabelOption.id == label_option_id))

    if option is None:
        raise ResourceNotFoundError

    for name, value in data.model_dump(exclude_unset=True).items():
        setattr(option, name, value)


@transactional
async def delete_label_option(*, db: AsyncSession, label_option_id: UUID) -> None:
    option = await db.scalar(select(LabelOption).where(LabelOption.id == label_option_id))

    if option is None:
        raise ResourceNotFoundError

    await db.execute(update(AudioSegment).where(AudioSegment.label_option_id == option.id).values(label_option_id=None))

    await db.execute(delete(audio_capture_label_table).where(audio_capture_label_table.c.label_option_id == option.id))

    option.is_deleted = True


async def get_audio_capture_list(
    *, db: AsyncSession, query: GetAudioCaptureListRequest
) -> tuple[list[GetAudioCaptureListItemDTO], int]:
    if query.label_option_ids == []:
        return [], 0

    stmt = select(AudioCapture)

    if query.firebase_anon_uid is not None:
        stmt = stmt.where(AudioCapture.firebase_anon_uid == query.firebase_anon_uid)

    if query.date_from is not None:
        stmt = stmt.where(AudioCapture.captured_at >= query.date_from)

    if query.date_to is not None:
        stmt = stmt.where(AudioCapture.captured_at <= query.date_to)

    if query.word_label is not None:
        stmt = stmt.join(Word, AudioCapture.word_id == Word.id).where(Word.label == query.word_label)

    if query.label_option_ids is not None:
        stmt = stmt.where(
            select(audio_capture_label_table.c.label_option_id)
            .where(audio_capture_label_table.c.audio_capture_id == AudioCapture.id)
            .where(audio_capture_label_table.c.label_option_id.in_(query.label_option_ids))
            .exists()
        )

    if query.has_memo is not None:
        memo_exists = (
            select(AudioSegment.id)
            .where(AudioSegment.audio_capture_id == AudioCapture.id, AudioSegment.memo.is_not(None))
            .exists()
        )
        stmt = stmt.where(memo_exists if query.has_memo else ~memo_exists)

    result = await db.execute(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    total = result.scalar_one()

    prev = (query.page - 1) * query.count_by_page
    limit = query.count_by_page
    captures = list(await db.scalars(stmt.order_by(AudioCapture.created_at.desc()).offset(prev).limit(limit)))

    counts = {}

    if captures:
        rows = await db.execute(
            select(
                AudioSegment.audio_capture_id,
                func.count(AudioSegment.id),
                func.count(AudioSegment.label_option_id),
                func.count(AudioSegment.memo),
            )
            .where(AudioSegment.audio_capture_id.in_([capture.id for capture in captures]))
            .group_by(AudioSegment.audio_capture_id)
        )

        counts = {row[0]: (row[1], row[2], row[3]) for row in rows}

    return [
        GetAudioCaptureListItemDTO(
            **GetAudioCaptureDTO.model_validate(capture, from_attributes=True).model_dump(),
            segment_count=counts.get(capture.id, (0, 0, 0))[0],
            labeled_count=counts.get(capture.id, (0, 0, 0))[1],
            has_memo=counts.get(capture.id, (0, 0, 0))[2] > 0,
            label_option_ids=[option.id for option in capture.label_options],
        )
        for capture in captures
    ], total


async def get_audio_capture_detail(
    *, db: AsyncSession, storage: S3StorageClient, audio_capture_id: UUID
) -> GetAudioCaptureDetailDTO:
    capture = await db.scalar(select(AudioCapture).where(AudioCapture.id == audio_capture_id))

    if capture is None:
        raise ResourceNotFoundError

    segments = await db.scalars(
        select(AudioSegment).where(AudioSegment.audio_capture_id == capture.id).order_by(AudioSegment.start_ms)
    )

    segment_data = [
        GetAudioSegmentDTO(
            id=segment.id,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            label_option_id=segment.label_option_id,
            memo=segment.memo,
            audio_url=storage.generate_presigned_url(
                path=f"{segment.audio_file.file_path}/{segment.audio_file.file_name}"
            ),
        )
        for segment in segments
    ]

    return GetAudioCaptureDetailDTO(
        **GetAudioCaptureDTO.model_validate(capture, from_attributes=True).model_dump(),
        parrot_species=capture.parrot_species,
        parrot_birthdate=capture.parrot_birthdate,
        device_platform=capture.device_platform,
        device_os_version=capture.device_os_version,
        device_model=capture.device_model,
        memo=capture.memo,
        audio_url=storage.generate_presigned_url(path=f"{capture.audio_file.file_path}/{capture.audio_file.file_name}"),
        segments=segment_data,
        label_option_ids=[option.id for option in capture.label_options],
    )


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


async def _save_audio_segment(
    *, db: AsyncSession, storage: S3StorageClient, segment: AudioSegment, content: bytes
) -> None:
    file_id = segment.audio_file.id
    path = f"{segment.audio_file.file_path}/{segment.audio_file.file_name}"
    uploaded = False

    try:
        try:
            await storage.upload(path=path, file=content)
            uploaded = True
            await db.flush()
        except Exception as exc:
            await db.rollback()

            if uploaded:
                try:
                    await storage.delete(path=path)
                except Exception:
                    logger.exception("업로드된 오디오 파일 정리 실패")

                if isinstance(exc, StaleDataError):
                    raise AudioSegmentSaveConflictError from exc
            raise

        try:
            await db.commit()
        except Exception:
            await db.rollback()

            async with session_factory() as check_db:
                saved = await check_db.scalar(
                    select(File.id).where(File.id == file_id).execution_options(include_deleted=True)
                )

            if saved is None:
                raise
    except asyncio.CancelledError:
        with suppress(Exception):
            await db.rollback()
        raise


@retry(
    retry=retry_if_exception_type(AudioSegmentSaveConflictError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
async def create_audio_segment(
    *, db: AsyncSession, storage: S3StorageClient, audio_capture_id: UUID, data: CreateAudioSegmentRequest
) -> None:
    capture = await db.scalar(select(AudioCapture).where(AudioCapture.id == audio_capture_id))

    if capture is None:
        raise ResourceNotFoundError

    if data.end_ms <= data.start_ms:
        raise InvalidAudioSegmentRangeError

    source = await storage.download(path=f"{capture.audio_file.file_path}/{capture.audio_file.file_name}")

    content = audio.trim(file=source, start_ms=data.start_ms, end_ms=data.end_ms)
    segment_id = uuid7()
    segment = AudioSegment(
        id=segment_id,
        audio_capture_id=capture.id,
        start_ms=data.start_ms,
        end_ms=data.end_ms,
        audio_file=_create_audio_file(
            name=capture.audio_file.file_name,
            path=f"audio_capture/{capture.firebase_anon_uid}/{capture.id}/segments/{segment_id}",
            content=content,
        ),
        label_option_id=None,
        memo=None,
        is_deleted=False,
    )
    db.add(segment)

    await _save_audio_segment(db=db, storage=storage, segment=segment, content=content)


@retry(
    retry=retry_if_exception_type(AudioSegmentSaveConflictError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
async def trim_audio_segment(
    *, db: AsyncSession, storage: S3StorageClient, audio_segment_id: UUID, data: TrimAudioSegmentRequest
) -> None:
    segment = await db.scalar(select(AudioSegment).where(AudioSegment.id == audio_segment_id))

    if segment is None:
        raise ResourceNotFoundError

    capture = await db.scalar(select(AudioCapture).where(AudioCapture.id == segment.audio_capture_id))

    if capture is None:
        raise ResourceNotFoundError

    if data.end_ms <= data.start_ms:
        raise InvalidAudioSegmentRangeError

    source = await storage.download(path=f"{capture.audio_file.file_path}/{capture.audio_file.file_name}")

    content = audio.trim(file=source, start_ms=data.start_ms, end_ms=data.end_ms)
    old_file = segment.audio_file
    new_file = _create_audio_file(name=old_file.file_name, path=old_file.file_path.rsplit("/", 1)[0], content=content)
    segment.audio_file = new_file
    segment.start_ms, segment.end_ms = data.start_ms, data.end_ms
    old_file.is_deleted = True

    await _save_audio_segment(db=db, storage=storage, segment=segment, content=content)


@transactional
async def delete_audio_segment(*, db: AsyncSession, audio_segment_id: UUID) -> None:
    segment = await db.scalar(select(AudioSegment).where(AudioSegment.id == audio_segment_id))

    if segment is None:
        raise ResourceNotFoundError

    segment.audio_file.is_deleted = True
    segment.is_deleted = True


@transactional
async def assign_audio_segment_label(
    *, db: AsyncSession, audio_segment_id: UUID, data: AssignAudioSegmentLabelRequest
) -> None:
    segment = await db.scalar(select(AudioSegment).where(AudioSegment.id == audio_segment_id))

    if segment is None:
        raise ResourceNotFoundError

    option = await db.scalar(select(LabelOption).where(LabelOption.id == data.label_option_id))

    if option is None:
        raise ResourceNotFoundError

    category = await db.scalar(select(LabelCategory).where(LabelCategory.id == option.category_id))

    if category is None:
        raise ResourceNotFoundError

    if category.target != LabelCategoryTargetEnum.SEGMENT:
        raise InvalidLabelCategoryTargetError

    segment.label_option_id = option.id


@transactional
async def assign_audio_capture_labels(
    *, db: AsyncSession, audio_capture_id: UUID, data: AssignAudioCaptureLabelsRequest
) -> None:
    capture = await db.scalar(select(AudioCapture).where(AudioCapture.id == audio_capture_id))

    if capture is None:
        raise ResourceNotFoundError

    ids = list(set(data.label_option_ids))

    if not ids:
        capture.label_options = []

        return

    options = list(await db.scalars(select(LabelOption).where(LabelOption.id.in_(ids))))

    if len(options) != len(ids):
        raise ResourceNotFoundError

    category_ids = {option.category_id for option in options}
    categories = list(await db.scalars(select(LabelCategory).where(LabelCategory.id.in_(category_ids))))

    if len(categories) != len(category_ids):
        raise ResourceNotFoundError

    if any(category.target != LabelCategoryTargetEnum.CAPTURE for category in categories):
        raise InvalidLabelCategoryTargetError

    capture.label_options = options


@transactional
async def update_audio_capture_memo(
    *, db: AsyncSession, audio_capture_id: UUID, data: UpdateAudioCaptureMemoRequest
) -> None:
    capture = await db.scalar(select(AudioCapture).where(AudioCapture.id == audio_capture_id))

    if capture is None:
        raise ResourceNotFoundError

    capture.memo = data.memo


@transactional
async def update_audio_segment_memo(
    *, db: AsyncSession, audio_segment_id: UUID, data: UpdateAudioSegmentMemoRequest
) -> None:
    segment = await db.scalar(select(AudioSegment).where(AudioSegment.id == audio_segment_id))

    if segment is None:
        raise ResourceNotFoundError

    segment.memo = data.memo


@transactional
async def _migrate_review(
    *,
    db: AsyncSession,
    capture: AudioCapture,
    options: list[LabelOption],
    memo: str | None,
) -> None:
    capture.label_options = options
    capture.memo = memo

    db.add(capture)


async def migrate_reviews(*, db: AsyncSession, data: MigrateReviewsRequest) -> dict[str, MigrateReviewResultDTO]:
    if not data.reviews:
        return {}

    if len(data.reviews) != len({review.audio_file_id for review in data.reviews}):
        raise DuplicateReviewAudioFileIdError

    paths = []

    for review in data.reviews:
        parts = review.audio_file_id.rsplit("/", 1)

        if len(parts) == 2:
            paths.append(tuple(parts))

    paths = list(dict.fromkeys(paths))
    captures = {}

    if paths:
        captures = {
            f"{capture.audio_file.file_path}/{capture.audio_file.file_name}": capture
            for capture in await db.scalars(
                select(AudioCapture)
                .join(File, AudioCapture.audio_file_id == File.id)
                .where(tuple_(File.file_path, File.file_name).in_(paths))
            )
        }

    names = list(dict.fromkeys(label.category for review in data.reviews for label in review.label))
    options = {}

    if names:
        categories = await db.scalars(
            select(LabelCategory).where(
                LabelCategory.name.in_(names), LabelCategory.target == LabelCategoryTargetEnum.CAPTURE
            )
        )

        options = {(category.name, option.name): option for category in categories for option in category.options}

    results = {}

    for review in data.reviews:
        capture = captures.get(review.audio_file_id)
        keys = dict.fromkeys((label.category, label.option) for label in review.label)

        if capture is None or any(key not in options for key in keys):
            results[review.audio_file_id] = MigrateReviewResultDTO(
                status="rejected",
                code=ResourceNotFoundError.code,
                error_code=ResourceNotFoundError.error_code,
                message=ResourceNotFoundError.message,
            )
            continue

        await _migrate_review(db=db, capture=capture, options=[options[key] for key in keys], memo=review.memo or None)

        results[review.audio_file_id] = MigrateReviewResultDTO(status="success")

    return results


async def export_audio_segments(
    *, db: AsyncSession, storage: S3StorageClient, audio_capture_label_option_ids: list[UUID] | None
) -> bytes:
    segments = []

    if audio_capture_label_option_ids != []:
        stmt = select(AudioSegment).where(AudioSegment.label_option_id.is_not(None))

        if audio_capture_label_option_ids is not None:
            stmt = stmt.where(
                select(audio_capture_label_table.c.label_option_id)
                .where(audio_capture_label_table.c.audio_capture_id == AudioSegment.audio_capture_id)
                .where(audio_capture_label_table.c.label_option_id.in_(audio_capture_label_option_ids))
                .exists()
            )

        segments = list(await db.scalars(stmt.order_by(AudioSegment.label_option_id, AudioSegment.created_at)))

    grouped = defaultdict(list)

    for segment in segments:
        grouped[segment.label_option_id].append(segment)

    categories = await get_label_list(db=db)

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for category in categories:
            for option in category.options:
                contents = await asyncio.gather(
                    *(
                        storage.download(path=f"{segment.audio_file.file_path}/{segment.audio_file.file_name}")
                        for segment in grouped[option.id]
                    )
                )

                for index, content in enumerate(contents, start=1):
                    archive.writestr(f"{category.name}/{option.name}/{index:03d}.wav", content)

    return buffer.getvalue()
