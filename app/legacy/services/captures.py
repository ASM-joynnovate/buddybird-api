import asyncio
import io
import logging
import wave
import zipfile
from uuid import UUID, uuid7

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defaultload, raiseload

from app.db import get_or_404, transactional
from app.errors import CustomError, ResourceNotFoundError
from app.legacy.errors import (
    AudioCaptureArchiveEntryNotFoundError,
    AudioCaptureArchiveInvalidError,
    InvalidLabelCategoryTargetError,
    NotAllowedFileTypeError,
)
from app.legacy.models import (
    AudioCapture,
    AudioSegment,
    LabelCategory,
    LabelCategoryTargetEnum,
    LabelOption,
    Word,
    audio_capture_label_table,
)
from app.legacy.schemas.captures import (
    AssignAudioCaptureLabelsRequest,
    BatchCreateAudioCaptureRequest,
    BatchCreateAudioCaptureResultDTO,
    GetAudioCaptureDetailDTO,
    GetAudioCaptureDTO,
    GetAudioCaptureListItemDTO,
    GetAudioCaptureListRequest,
    GetWordDTO,
    UpdateAudioCaptureMemoRequest,
)
from app.legacy.schemas.segments import GetAudioSegmentDTO
from app.legacy.services.segments import create_audio_file
from app.s3 import S3StorageClient

logger = logging.getLogger(__name__)


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

    if query.parrot_species is not None:
        stmt = stmt.where(AudioCapture.parrot_species == query.parrot_species)

    if query.device_model is not None:
        stmt = stmt.where(AudioCapture.device_model == query.device_model)

    if query.device_platform is not None:
        stmt = stmt.where(AudioCapture.device_platform == query.device_platform)

    if query.device_os_version is not None:
        stmt = stmt.where(AudioCapture.device_os_version == query.device_os_version)

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
    captures = list(
        await db.scalars(
            stmt.options(raiseload(AudioCapture.audio_file), defaultload(AudioCapture.word).raiseload(Word.audio_file))
            .order_by(AudioCapture.created_at.desc())
            .offset(prev)
            .limit(limit)
        )
    )

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
            parrot_species=capture.parrot_species,
            device_platform=capture.device_platform,
            device_os_version=capture.device_os_version,
            device_model=capture.device_model,
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
    capture = await get_or_404(db=db, model=AudioCapture, id=audio_capture_id)

    segments = list(
        await db.scalars(
            select(AudioSegment).where(AudioSegment.audio_capture_id == capture.id).order_by(AudioSegment.start_ms)
        )
    )

    keys = [capture.audio_file.object_key, *(segment.audio_file.object_key for segment in segments)]
    urls = await asyncio.to_thread(lambda: [storage.generate_presigned_url(path=key) for key in keys])

    segment_data = [
        GetAudioSegmentDTO(
            id=segment.id,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            label_option_id=segment.label_option_id,
            memo=segment.memo,
            audio_url=url,
        )
        for segment, url in zip(segments, urls[1:], strict=True)
    ]

    return GetAudioCaptureDetailDTO(
        **GetAudioCaptureDTO.model_validate(capture, from_attributes=True).model_dump(exclude={"word"}),
        word=GetWordDTO.model_validate(capture.word, from_attributes=True) if capture.word is not None else None,
        parrot_species=capture.parrot_species,
        parrot_birthdate=capture.parrot_birthdate,
        device_platform=capture.device_platform,
        device_os_version=capture.device_os_version,
        device_model=capture.device_model,
        memo=capture.memo,
        audio_url=urls[0],
        segments=segment_data,
        label_option_ids=[option.id for option in capture.label_options],
    )


@transactional
async def assign_audio_capture_labels(
    *, db: AsyncSession, audio_capture_id: UUID, data: AssignAudioCaptureLabelsRequest
) -> None:
    capture = await get_or_404(db=db, model=AudioCapture, id=audio_capture_id)
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
    capture = await get_or_404(db=db, model=AudioCapture, id=audio_capture_id)

    capture.memo = data.memo


@transactional
async def save_audio_captures(*, db: AsyncSession, captures: list[AudioCapture]) -> None:
    db.add_all(captures)


async def batch_create_audio_capture(
    *, db: AsyncSession, storage: S3StorageClient, data: BatchCreateAudioCaptureRequest
) -> dict[str, BatchCreateAudioCaptureResultDTO]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(await data.file.read()))
    except zipfile.BadZipFile as exc:
        raise AudioCaptureArchiveInvalidError from exc

    saved_ids = set(
        await db.scalars(
            select(AudioCapture.client_capture_id).where(
                AudioCapture.firebase_anon_uid == data.firebase_anon_uid,
                AudioCapture.client_capture_id.in_([item.client_capture_id for item in data.metadata]),
            )
        )
    )

    results = {}
    pending = []

    with archive:
        for item in data.metadata:
            if item.client_capture_id in saved_ids:
                results[item.client_capture_id] = BatchCreateAudioCaptureResultDTO(status="success")
                continue

            capture_id = uuid7()

            try:
                try:
                    content = archive.read(item.file_name)
                except KeyError as exc:
                    raise AudioCaptureArchiveEntryNotFoundError from exc
                except zipfile.BadZipFile as exc:
                    raise AudioCaptureArchiveInvalidError from exc

                is_wav = content[:4] == b"RIFF" and content[8:12] == b"WAVE"

                if not is_wav:
                    raise NotAllowedFileTypeError

                file = create_audio_file(
                    name=item.file_name,
                    path=f"audio_capture/{data.firebase_anon_uid}/{capture_id}",
                    content=content,
                )
            except CustomError as exc:
                results[item.client_capture_id] = BatchCreateAudioCaptureResultDTO(
                    status="rejected",
                    code=exc.code,
                    error_code=exc.error_code,
                    message=exc.message,
                )
                continue

            try:
                with wave.open(io.BytesIO(content), "rb") as wav:
                    frames = wav.getnframes()
                    rate = wav.getframerate()
            except wave.Error, EOFError:
                frames = 0
                rate = 0

            capture = AudioCapture(
                id=capture_id,
                firebase_anon_uid=data.firebase_anon_uid,
                client_capture_id=item.client_capture_id,
                client_session_id=item.client_session_id,
                word_id=None,
                client_word_id=item.client_word_id,
                cycle=item.cycle,
                phase=item.phase,
                captured_at=item.captured_at,
                duration_ms=int(frames / rate * 1000) if rate else None,
                audio_file=file,
                parrot_species=item.parrot_species,
                parrot_birthdate=item.parrot_birthdate,
                app_version=item.app_version,
                device_platform=data.device_platform,
                device_os_version=data.device_os_version,
                device_model=data.device_model,
                memo=None,
                is_deleted=False,
            )

            pending.append((capture, content))
            saved_ids.add(item.client_capture_id)
            results[item.client_capture_id] = BatchCreateAudioCaptureResultDTO(status="success")

    try:
        for capture, content in pending:
            await storage.upload(path=capture.audio_file.object_key, file=content)

        await save_audio_captures(db=db, captures=[capture for capture, _ in pending])
    except Exception:
        for capture, _ in pending:
            try:
                await storage.delete(path=capture.audio_file.object_key)
            except Exception:
                logger.exception("업로드된 오디오 파일 정리 실패")

        raise

    return results
