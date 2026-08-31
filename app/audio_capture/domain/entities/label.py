from dataclasses import dataclass, field
from uuid import UUID, uuid7

from app.audio_capture.domain.commands import (
    CreateLabelCategoryCommand,
    CreateLabelOptionCommand,
    UpdateLabelCategoryCommand,
    UpdateLabelOptionCommand,
)
from app.audio_capture.domain.enums import LabelCategoryTargetEnum
from app.audio_capture.domain.errors import InvalidLabelCategoryTargetError
from core.common.entity import AggregateRoot, Entity
from core.common.sentinel import MISSING


@dataclass(eq=False)
class LabelOption(Entity):
    category_id: UUID
    name: str
    display_order: int
    is_deleted: bool

    @classmethod
    def create(cls, *, command: CreateLabelOptionCommand) -> LabelOption:
        label_option_id = uuid7()
        return cls(
            id=label_option_id,
            category_id=command.category_id,
            name=command.name,
            display_order=command.display_order,
            is_deleted=False,
        )

    def update(self, *, command: UpdateLabelOptionCommand) -> None:
        if command.name is not MISSING:
            self.name = command.name
        if command.display_order is not MISSING:
            self.display_order = command.display_order

    def delete(self) -> None:
        self.is_deleted = True


@dataclass(eq=False)
class LabelCategory(AggregateRoot):
    name: str
    display_order: int
    is_deleted: bool
    target: LabelCategoryTargetEnum
    options: list[LabelOption] = field(default_factory=list)

    @classmethod
    def create(cls, *, command: CreateLabelCategoryCommand) -> LabelCategory:
        label_category_id = uuid7()
        return cls(
            id=label_category_id,
            name=command.name,
            display_order=command.display_order,
            is_deleted=False,
            target=command.target,
            options=[],
        )

    def update(self, *, command: UpdateLabelCategoryCommand) -> None:
        if command.name is not MISSING:
            self.name = command.name
        if command.display_order is not MISSING:
            self.display_order = command.display_order

    def ensure_target(self, *, target: LabelCategoryTargetEnum) -> None:
        if self.target != target:
            raise InvalidLabelCategoryTargetError

    def delete(self) -> None:
        self.is_deleted = True
