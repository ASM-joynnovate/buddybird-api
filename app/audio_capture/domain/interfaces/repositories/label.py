from abc import ABC, abstractmethod
from uuid import UUID

from app.audio_capture.domain.entities.label import LabelCategory, LabelOption
from app.audio_capture.domain.enums import LabelCategoryTargetEnum


class ILabelCategoryRepo(ABC):
    @abstractmethod
    async def get_list(self) -> list[LabelCategory]: ...

    @abstractmethod
    async def get_by_id(self, *, label_category_id: UUID) -> LabelCategory | None: ...

    @abstractmethod
    async def get_by_ids(self, *, label_category_ids: list[UUID]) -> list[LabelCategory]: ...

    @abstractmethod
    async def exists_by_name_and_target(self, *, name: str, target: LabelCategoryTargetEnum) -> bool: ...

    @abstractmethod
    async def save(self, *, label_category: LabelCategory) -> None: ...


class ILabelOptionRepo(ABC):
    @abstractmethod
    async def get_by_id(self, *, label_option_id: UUID) -> LabelOption | None: ...

    @abstractmethod
    async def get_by_ids(self, *, label_option_ids: list[UUID]) -> list[LabelOption]: ...

    @abstractmethod
    async def exists_by_category_id_and_name(self, *, category_id: UUID, name: str) -> bool: ...

    @abstractmethod
    async def get_by_category_name_and_option_name_and_target(
        self, *, category_name: str, option_name: str, target: LabelCategoryTargetEnum
    ) -> LabelOption | None: ...

    @abstractmethod
    async def save(self, *, label_option: LabelOption) -> None: ...
