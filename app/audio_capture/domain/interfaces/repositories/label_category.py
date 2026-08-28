from abc import ABC, abstractmethod
from uuid import UUID

from app.audio_capture.domain.entities.label import LabelCategory
from app.audio_capture.domain.enum import LabelCategoryTargetEnum


class ILabelCategoryRepo(ABC):
    @abstractmethod
    async def get_list(self) -> list[LabelCategory]:
        pass

    @abstractmethod
    async def get_by_id(self, *, label_category_id: UUID) -> LabelCategory | None:
        pass

    @abstractmethod
    async def get_by_ids(self, *, label_category_ids: list[UUID]) -> list[LabelCategory]:
        pass

    @abstractmethod
    async def exists_by_name_and_target(self, *, name: str, target: LabelCategoryTargetEnum) -> bool:
        pass

    @abstractmethod
    async def save(self, *, label_category: LabelCategory) -> None:
        pass
