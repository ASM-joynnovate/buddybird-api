from uuid import UUID

from sqlalchemy import select

from app.audio_capture.domain.entities.label import LabelCategory, LabelOption
from app.audio_capture.domain.enums import LabelCategoryTargetEnum
from app.audio_capture.domain.interfaces.repositories import ILabelCategoryRepo, ILabelOptionRepo
from core.db import session, session_factory


class LabelCategorySQLAlchemyRepo(ILabelCategoryRepo):
    async def get_list(self) -> list[LabelCategory]:
        async with session_factory() as read_session:
            stmt = select(LabelCategory).order_by(LabelCategory.display_order)

            result = await read_session.execute(stmt)

            return list(result.scalars().all())

    async def get_by_id(self, *, label_category_id: UUID) -> LabelCategory | None:
        stmt = select(LabelCategory).where(LabelCategory.id == label_category_id)

        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_by_ids(self, *, label_category_ids: list[UUID]) -> list[LabelCategory]:
        if not label_category_ids:
            return []

        stmt = select(LabelCategory).where(LabelCategory.id.in_(label_category_ids))

        result = await session.execute(stmt)

        return list(result.scalars().all())

    async def get_by_names_and_target(
        self, *, names: list[str], target: LabelCategoryTargetEnum
    ) -> list[LabelCategory]:
        if not names:
            return []

        stmt = select(LabelCategory).where(LabelCategory.name.in_(names)).where(LabelCategory.target == target)

        result = await session.execute(stmt)

        return list(result.scalars().all())

    async def exists_by_name_and_target(self, *, name: str, target: LabelCategoryTargetEnum) -> bool:
        async with session_factory() as read_session:
            stmt = (
                select(LabelCategory.id)
                .where(LabelCategory.name == name)
                .where(LabelCategory.target == target)
                .limit(1)
            )

            result = await read_session.execute(stmt)

            return result.scalar_one_or_none() is not None

    async def save(self, *, label_category: LabelCategory) -> None:
        session.add(label_category)


class LabelOptionSQLAlchemyRepo(ILabelOptionRepo):
    async def get_by_id(self, *, label_option_id: UUID) -> LabelOption | None:
        stmt = select(LabelOption).where(LabelOption.id == label_option_id)

        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_by_ids(self, *, label_option_ids: list[UUID]) -> list[LabelOption]:
        if not label_option_ids:
            return []

        stmt = select(LabelOption).where(LabelOption.id.in_(label_option_ids))

        result = await session.execute(stmt)

        return list(result.scalars().all())

    async def exists_by_category_id_and_name(self, *, category_id: UUID, name: str) -> bool:
        async with session_factory() as read_session:
            stmt = (
                select(LabelOption.id)
                .where(LabelOption.category_id == category_id)
                .where(LabelOption.name == name)
                .limit(1)
            )

            result = await read_session.execute(stmt)

            return result.scalar_one_or_none() is not None

    async def get_by_category_name_and_option_name_and_target(
        self, *, category_name: str, option_name: str, target: LabelCategoryTargetEnum
    ) -> LabelOption | None:
        stmt = (
            select(LabelOption)
            .join(LabelCategory, LabelOption.category_id == LabelCategory.id)
            .where(LabelCategory.name == category_name)
            .where(LabelOption.name == option_name)
            .where(LabelCategory.target == target)
        )

        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    async def save(self, *, label_option: LabelOption) -> None:
        session.add(label_option)
