import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from app.audio_capture.domain.command import CreateAudioCaptureCommand
from app.audio_capture.domain.enum import PhaseEnum
from app.shared_kernel.domain.command.file import CreateFileCommand
from app.shared_kernel.domain.entities.file import File
from core.common.entity import AggregateRoot


@dataclass(eq=False, slots=True)
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
    created_at: datetime
    updated_at: datetime | None
    is_deleted: bool

    @classmethod
    def create(cls, *, command: CreateAudioCaptureCommand) -> AudioCapture:
        audio_capture_id = uuid.uuid7()

        file = File.create(
            command=CreateFileCommand(
                name=command.audio_file.name,
                path=f"audio_capture/{command.firebase_anon_uid}/{audio_capture_id}",
                type=command.audio_file.type,
                file=command.audio_file.file,
            )
        )
        file.validate(
            allowed_types=["audio/wav", "audio/x-wav", "audio/vnd.wave", "audio/wave"],
            max_size="1MB",
        )

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
            created_at=datetime.now(UTC),
            updated_at=None,
            is_deleted=False,
        )

    def delete(self):
        if self.audio_file is not None:
            self.audio_file.delete()
        self.is_deleted = True
