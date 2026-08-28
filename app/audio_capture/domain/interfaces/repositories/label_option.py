from abc import ABC, abstractmethod
from uuid import UUID

from app.audio_capture.domain.entities.label import LabelOption


class ILabelOptionRepo(ABC):
    @abstractmethod
    async def get_by_id(self, *, label_option_id: UUID) -> LabelOption | None:
        pass

    @abstractmethod
    async def get_by_ids(self, *, label_option_ids: list[UUID]) -> list[LabelOption]:
        pass

    @abstractmethod
    async def exists_by_category_id_and_name(self, *, category_id: UUID, name: str) -> bool:
        pass

    @abstractmethod
    async def save(self, *, label_option: LabelOption) -> None:
        pass
