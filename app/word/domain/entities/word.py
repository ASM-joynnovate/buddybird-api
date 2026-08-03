from dataclasses import dataclass
from datetime import UTC, datetime

from app.shared_kernel.domain.command.file import CreateFileCommand
from app.shared_kernel.domain.entities.file import File
from app.word.domain.command import CreateWordCommand
from core.common.entity import AggregateRoot


@dataclass(eq=False, slots=True)
class Word(AggregateRoot):
    label: str
    firebase_anon_uid: str | None
    client_word_id: str
    is_preset: bool
    audio_file: File
    device_platform: str | None
    device_os_version: str | None
    device_model: str | None
    created_at: datetime
    updated_at: datetime | None
    is_deleted: bool

    @classmethod
    def create(cls, *, command: CreateWordCommand) -> Word:
        file = File.create(
            command=CreateFileCommand(
                name=command.audio_file.name,
                path=f"word/{command.firebase_anon_uid}",
                type=command.audio_file.type,
                file=command.audio_file.file,
            )
        )
        file.validate(allowed_types=["audio/mpeg", "audio/wav", "audio/x-wav", "audio/aac"], max_size="5MB")

        return cls(
            label=command.label,
            firebase_anon_uid=command.firebase_anon_uid,
            client_word_id=command.client_word_id,
            audio_file=file,
            is_preset=False,
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
