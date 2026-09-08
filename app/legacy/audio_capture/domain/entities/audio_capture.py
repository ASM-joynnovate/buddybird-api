from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from app.legacy.audio_capture.domain.commands import (
    AssignAudioCaptureLabelsCommand,
    UpdateAudioCaptureMemoCommand,
)
from app.legacy.audio_capture.domain.entities.label import LabelOption
from app.legacy.audio_capture.domain.enums import PhaseEnum
from app.shared_kernel.domain.entities.file import File
from core.common.entity import AggregateRoot


@dataclass(eq=False)
class AudioCapture(AggregateRoot):
    client_capture_id: str
    client_session_id: str
    firebase_anon_uid: str
    word_id: UUID | None
    client_word_id: str
    cycle: int
    phase: PhaseEnum
    captured_at: datetime
    duration_ms: int | None
    audio_file: File
    parrot_species: str | None
    parrot_birthdate: date | None
    app_version: str | None
    device_platform: str | None
    device_os_version: str | None
    device_model: str | None
    memo: str | None
    is_deleted: bool
    label_options: list[LabelOption] = field(default_factory=list)

    def update_memo(self, *, command: UpdateAudioCaptureMemoCommand) -> None:
        self.memo = command.memo

    def assign_labels(self, *, command: AssignAudioCaptureLabelsCommand) -> None:
        self.label_options = command.label_options
