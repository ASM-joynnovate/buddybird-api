from datetime import datetime, UTC
from dataclasses import dataclass

from app.shared_kernel.domain.command.file import CreateFileCommand
from app.shared_kernel.domain.entities.file import File
from app.word.domain.command import CreateWordCommand
from core.common.entity import AggregateRoot


@dataclass(eq=False, slots=True)
class Word(AggregateRoot):
    label: str
    firebase_anon_uid: str
    is_preset: bool
    audio_file: File | None
    device_platform: str | None
    device_os_version: str | None
    device_model: str | None
    created_at: datetime
    updated_at: datetime | None
    is_deleted: bool

    @classmethod
    def create(
            cls,
            *,
            command: CreateWordCommand
    ) -> "Word":
        word = cls(
            label=command.label,
            firebase_anon_uid=command.firebase_anon_id,
            audio_file=None,
            is_preset=False,
            device_platform=command.device_platform,
            device_os_version=command.device_os_version,
            device_model=command.device_model,
            created_at=datetime.now(UTC),
            updated_at=None,
            is_deleted=False,
        )

        file = File.create(
            command=CreateFileCommand(
                name=command.audio_file.name,
                path=f"word/{word.id}",
                type=command.audio_file.type,
                file=command.audio_file.file
            )
        )
        file.validate(allowed_types=["audio/mpeg", "audio/wav", "audio/aac"], max_size="5MB")
        word.audio_file = file

        return word

    def delete(self):
        if self.audio_file is not None:
            self.audio_file.delete()
        self.is_deleted = True