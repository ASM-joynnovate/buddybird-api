from dataclasses import dataclass
from uuid import UUID

from app.audio_capture.domain.enums import LabelCategoryTargetEnum
from core.common.sentinel import MISSING


@dataclass(frozen=True)
class CreateLabelCategoryCommand:
    name: str
    display_order: int
    target: LabelCategoryTargetEnum


@dataclass(frozen=True)
class UpdateLabelCategoryCommand:
    name: str | MISSING
    display_order: int | MISSING


@dataclass(frozen=True)
class CreateLabelOptionCommand:
    category_id: UUID
    name: str
    display_order: int


@dataclass(frozen=True)
class UpdateLabelOptionCommand:
    name: str | MISSING
    display_order: int | MISSING
