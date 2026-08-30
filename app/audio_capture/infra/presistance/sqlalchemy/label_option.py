from uuid import UUID

from sqlalchemy import select

from app.audio_capture.domain.entities.label import LabelOption
from app.audio_capture.domain.enum import LabelCategoryTargetEnum
from app.audio_capture.domain.interfaces.repositories.label_option import ILabelOptionRepo
from core.db import session, session_factory
from core.db.sqlalchemy.models import label_category_table


class SQLAlchemyLabelOptionRepo(ILabelOptionRepo):
    async def get_by_id(self, *, label_option_id: UUID) -> LabelOption | None:
        result = await session.execute(
            select(LabelOption).where(LabelOption.id == label_option_id).where(LabelOption.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, *, label_option_ids: list[UUID]) -> list[LabelOption]:
        if not label_option_ids:
            return []
        result = await session.execute(
            select(LabelOption).where(LabelOption.id.in_(label_option_ids)).where(LabelOption.is_deleted.is_(False))
        )
        return list(result.scalars().all())

    async def exists_by_category_id_and_name(self, *, category_id: UUID, name: str) -> bool:
        async with session_factory() as read_session:
            result = await read_session.execute(
                select(LabelOption.id)
                .where(LabelOption.category_id == category_id)
                .where(LabelOption.name == name)
                .where(LabelOption.is_deleted.is_(False))
                .limit(1)
            )
            return result.scalar_one_or_none() is not None

    async def get_by_category_name_and_option_name_and_target(
        self, *, category_name: str, option_name: str, target: LabelCategoryTargetEnum
    ) -> LabelOption | None:
        stmt = (
            select(LabelOption)
            .join(label_category_table, LabelOption.category_id == label_category_table.c.id)
            .where(label_category_table.c.name == category_name)
            .where(LabelOption.name == option_name)
            .where(label_category_table.c.target == target)
            .where(label_category_table.c.is_deleted.is_(False))
            .where(LabelOption.is_deleted.is_(False))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, *, label_option: LabelOption) -> None:
        session.add(label_option)
