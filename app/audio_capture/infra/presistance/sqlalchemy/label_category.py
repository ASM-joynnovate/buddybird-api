from uuid import UUID

from sqlalchemy import select

from app.audio_capture.domain.entities.label import LabelCategory
from app.audio_capture.domain.enum import LabelCategoryTargetEnum
from app.audio_capture.domain.interfaces.repositories.label_category import ILabelCategoryRepo
from core.db import session, session_factory


class SQLAlchemyLabelCategoryRepo(ILabelCategoryRepo):
    async def get_list(self) -> list[LabelCategory]:
        async with session_factory() as read_session:
            result = await read_session.execute(
                select(LabelCategory).where(LabelCategory.is_deleted.is_(False)).order_by(LabelCategory.display_order)
            )
            return result.scalars().all()

    async def get_by_id(self, *, label_category_id: UUID) -> LabelCategory | None:
        result = await session.execute(
            select(LabelCategory)
            .where(LabelCategory.id == label_category_id)
            .where(LabelCategory.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, *, label_category_ids: list[UUID]) -> list[LabelCategory]:
        if not label_category_ids:
            return []
        result = await session.execute(
            select(LabelCategory)
            .where(LabelCategory.id.in_(label_category_ids))
            .where(LabelCategory.is_deleted.is_(False))
        )
        return list(result.scalars().all())

    async def exists_by_name_and_target(self, *, name: str, target: LabelCategoryTargetEnum) -> bool:
        async with session_factory() as read_session:
            result = await read_session.execute(
                select(LabelCategory.id)
                .where(LabelCategory.name == name)
                .where(LabelCategory.target == target)
                .where(LabelCategory.is_deleted.is_(False))
                .limit(1)
            )
            return result.scalar_one_or_none() is not None

    async def save(self, *, label_category: LabelCategory) -> None:
        session.add(label_category)
