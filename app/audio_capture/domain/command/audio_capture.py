from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.audio_capture.domain.entities.label import LabelOption
from app.audio_capture.domain.enum import PhaseEnum
from app.shared_kernel.domain.command.file import AssignFileCommand


@dataclass
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


@dataclass
class AssignAudioCaptureLabelsCommand:
    label_options: list[LabelOption]
