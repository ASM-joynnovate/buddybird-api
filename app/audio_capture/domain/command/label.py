from dataclasses import dataclass
from uuid import UUID

from app.audio_capture.domain.enum import LabelCategoryTargetEnum


@dataclass
class CreateLabelCategoryCommand:
    name: str
    display_order: int
    target: LabelCategoryTargetEnum


@dataclass
class UpdateLabelCategoryCommand:
    name: str | None
    display_order: int | None


@dataclass
class CreateLabelOptionCommand:
    category_id: UUID
    name: str
    display_order: int


@dataclass
class UpdateLabelOptionCommand:
    name: str | None
    display_order: int | None
