from abc import ABC, abstractmethod
from uuid import UUID

from app.audio_capture.domain.entities.label import LabelCategory


class ILabelCategoryRepo(ABC):
    @abstractmethod
    async def get_list(self) -> list[LabelCategory]:
        pass

    @abstractmethod
    async def get_by_id(self, *, label_category_id: UUID) -> LabelCategory | None:
        pass

    @abstractmethod
    async def save(self, *, label_category: LabelCategory) -> None:
        pass
