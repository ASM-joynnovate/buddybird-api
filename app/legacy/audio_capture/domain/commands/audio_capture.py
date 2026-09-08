from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.legacy.audio_capture.domain.entities.label import LabelOption


@dataclass(frozen=True)
class AssignAudioCaptureLabelsCommand:
    label_options: list[LabelOption]


@dataclass(frozen=True)
class UpdateAudioCaptureMemoCommand:
    memo: str | None
