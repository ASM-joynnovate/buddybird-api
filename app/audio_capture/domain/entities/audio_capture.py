from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID, uuid7

from app.audio_capture.domain.commands import (
    AssignAudioCaptureLabelsCommand,
    CreateAudioCaptureCommand,
    UpdateAudioCaptureMemoCommand,
)
from app.audio_capture.domain.constants import ALLOWED_AUDIO_MIME_TYPES, MAX_AUDIO_FILE_SIZE
from app.audio_capture.domain.entities.label import LabelOption
from app.audio_capture.domain.enums import PhaseEnum
from app.shared_kernel.domain.commands import CreateFileCommand
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

    @classmethod
    def create(cls, *, command: CreateAudioCaptureCommand) -> AudioCapture:
        audio_capture_id = uuid7()

        file = File.create(
            command=CreateFileCommand(
                name=command.audio_file.name,
                path=f"audio_capture/{command.firebase_anon_uid}/{audio_capture_id}",
                type=command.audio_file.type,
                file=command.audio_file.file,
            )
        )
        file.validate(allowed_types=ALLOWED_AUDIO_MIME_TYPES, max_size=MAX_AUDIO_FILE_SIZE)

        return cls(
            id=audio_capture_id,
            client_capture_id=command.client_capture_id,
            client_session_id=command.client_session_id,
            firebase_anon_uid=command.firebase_anon_uid,
            word_id=command.word_id,
            client_word_id=command.client_word_id,
            cycle=command.cycle,
            phase=command.phase,
            captured_at=command.captured_at,
            duration_ms=command.duration_ms,
            audio_file=file,
            parrot_species=command.parrot_species,
            parrot_birthdate=command.parrot_birthdate,
            app_version=command.app_version,
            device_platform=command.device_platform,
            device_os_version=command.device_os_version,
            device_model=command.device_model,
            memo=None,
            is_deleted=False,
            label_options=[],
        )

    def update_memo(self, *, command: UpdateAudioCaptureMemoCommand) -> None:
        self.memo = command.memo

    def assign_labels(self, *, command: AssignAudioCaptureLabelsCommand) -> None:
        self.label_options = command.label_options

    def delete(self) -> None:
        self.audio_file.delete()
        self.is_deleted = True
