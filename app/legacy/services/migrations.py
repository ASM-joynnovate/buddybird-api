from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import ResourceNotFoundError
from app.legacy.errors import DuplicateReviewAudioFileIdError
from app.legacy.models import AudioCapture, LabelCategory, LabelCategoryTargetEnum, LabelOption
from app.legacy.schemas.captures import MigrateReviewResultDTO, MigrateReviewsRequest
from app.models import File


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
            capture.audio_file.object_key: capture
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
