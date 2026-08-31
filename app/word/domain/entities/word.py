from dataclasses import dataclass
from uuid import uuid7

from app.shared_kernel.domain.commands import CreateFileCommand
from app.shared_kernel.domain.entities.file import File
from app.word.domain.commands import CreateWordCommand
from app.word.domain.constants import ALLOWED_AUDIO_MIME_TYPES, MAX_AUDIO_FILE_SIZE
from core.common.entity import AggregateRoot


@dataclass(eq=False)
class Word(AggregateRoot):
    label: str
    firebase_anon_uid: str | None
    client_word_id: str
    is_preset: bool
    audio_file: File
    device_platform: str | None
    device_os_version: str | None
    device_model: str | None
    is_deleted: bool

    @classmethod
    def create(cls, *, command: CreateWordCommand) -> Word:
        word_id = uuid7()

        file = File.create(
            command=CreateFileCommand(
                name=command.audio_file.name,
                path=f"word/{command.firebase_anon_uid}/{word_id}",
                type=command.audio_file.type,
                file=command.audio_file.file,
            )
        )
        file.validate(allowed_types=ALLOWED_AUDIO_MIME_TYPES, max_size=MAX_AUDIO_FILE_SIZE)

        return cls(
            id=word_id,
            label=command.label,
            firebase_anon_uid=command.firebase_anon_uid,
            client_word_id=command.client_word_id,
            audio_file=file,
            is_preset=False,
            device_platform=command.device_platform,
            device_os_version=command.device_os_version,
            device_model=command.device_model,
            is_deleted=False,
        )

    def delete(self) -> None:
        self.audio_file.delete()
        self.is_deleted = True
