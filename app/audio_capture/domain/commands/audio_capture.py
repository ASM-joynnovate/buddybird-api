from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from app.audio_capture.domain.enums import PhaseEnum
from app.shared_kernel.domain.commands import AssignFileCommand

if TYPE_CHECKING:
    from app.audio_capture.domain.entities.label import LabelOption


@dataclass(frozen=True)
class CreateAudioCaptureCommand:
    client_capture_id: str
    client_session_id: str
    firebase_anon_uid: str
    word_id: UUID | None
    client_word_id: str
    cycle: int
    phase: PhaseEnum
    captured_at: datetime
    duration_ms: int | None
    audio_file: AssignFileCommand
    parrot_species: str | None
    parrot_birthdate: date | None
    app_version: str | None
    device_platform: str | None
    device_os_version: str | None
    device_model: str | None


@dataclass(frozen=True)
class AssignAudioCaptureLabelsCommand:
    label_options: list[LabelOption]


@dataclass(frozen=True)
class UpdateAudioCaptureMemoCommand:
    memo: str | None
