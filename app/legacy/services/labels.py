from uuid import UUID, uuid7

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_or_404, transactional
from app.legacy.errors import DuplicateLabelCategoryError, DuplicateLabelOptionError
from app.legacy.models import (
    AudioSegment,
    LabelCategory,
    LabelCategoryTargetEnum,
    LabelOption,
    audio_capture_label_table,
)
from app.legacy.schemas.labels import (
    CreateLabelCategoryRequest,
    CreateLabelOptionRequest,
    GetLabelCategoryDTO,
    GetLabelOptionDTO,
    UpdateLabelCategoryRequest,
    UpdateLabelOptionRequest,
)


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
    category = await get_or_404(db=db, model=LabelCategory, id=label_category_id)

    for name, value in data.model_dump(exclude_unset=True).items():
        setattr(category, name, value)


@transactional
async def delete_label_category(*, db: AsyncSession, label_category_id: UUID) -> None:
    category = await get_or_404(db=db, model=LabelCategory, id=label_category_id)
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
    await get_or_404(db=db, model=LabelCategory, id=label_category_id)

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
    option = await get_or_404(db=db, model=LabelOption, id=label_option_id)

    for name, value in data.model_dump(exclude_unset=True).items():
        setattr(option, name, value)


@transactional
async def delete_label_option(*, db: AsyncSession, label_option_id: UUID) -> None:
    option = await get_or_404(db=db, model=LabelOption, id=label_option_id)

    await db.execute(update(AudioSegment).where(AudioSegment.label_option_id == option.id).values(label_option_id=None))

    await db.execute(delete(audio_capture_label_table).where(audio_capture_label_table.c.label_option_id == option.id))

    option.is_deleted = True
