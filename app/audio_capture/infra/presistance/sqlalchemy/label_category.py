from uuid import UUID

from sqlalchemy import select

from app.audio_capture.domain.entities.label import LabelCategory
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

    async def save(self, *, label_category: LabelCategory) -> None:
        session.add(label_category)
