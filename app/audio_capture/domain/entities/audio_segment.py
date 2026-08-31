from dataclasses import dataclass
from uuid import UUID, uuid7

from app.audio_capture.domain.commands import (
    AssignAudioSegmentLabelCommand,
    CreateAudioSegmentCommand,
    TrimAudioSegmentCommand,
    UpdateAudioSegmentMemoCommand,
)
from app.audio_capture.domain.constants import ALLOWED_AUDIO_MIME_TYPES, MAX_AUDIO_FILE_SIZE
from app.audio_capture.domain.value_objects import AudioSegmentRange
from app.shared_kernel.domain.commands import CreateFileCommand
from app.shared_kernel.domain.entities.file import File
from core.common.entity import AggregateRoot


@dataclass(eq=False)
class AudioSegment(AggregateRoot):
    audio_capture_id: UUID
    range: AudioSegmentRange
    audio_file: File
    label_option_id: UUID | None
    memo: str | None
    is_deleted: bool

    @classmethod
    def create(cls, *, command: CreateAudioSegmentCommand) -> AudioSegment:
        segment_id = uuid7()

        file = File.create(
            command=CreateFileCommand(
                name=command.audio_file.name,
                path=f"audio_capture/{command.firebase_anon_uid}/{command.audio_capture_id}/segments/{segment_id}",
                type=command.audio_file.type,
                file=command.audio_file.file,
            )
        )
        file.validate(allowed_types=ALLOWED_AUDIO_MIME_TYPES, max_size=MAX_AUDIO_FILE_SIZE)

        return cls(
            id=segment_id,
            audio_capture_id=command.audio_capture_id,
            range=command.range,
            audio_file=file,
            label_option_id=None,
            memo=None,
            is_deleted=False,
        )

    def retrim(self, *, command: TrimAudioSegmentCommand) -> None:
        old_file = self.audio_file

        new_file = File.create(
            command=CreateFileCommand(
                name=command.audio_file.name,
                path=old_file.file_path.rsplit("/", 1)[0],
                type=command.audio_file.type,
                file=command.audio_file.file,
            )
        )
        new_file.validate(allowed_types=ALLOWED_AUDIO_MIME_TYPES, max_size=MAX_AUDIO_FILE_SIZE)

        self.range = command.range
        self.audio_file = new_file
        old_file.delete()

    def assign_label(self, *, command: AssignAudioSegmentLabelCommand) -> None:
        self.label_option_id = command.label_option_id

    def update_memo(self, *, command: UpdateAudioSegmentMemoCommand) -> None:
        self.memo = command.memo

    def delete(self) -> None:
        self.audio_file.delete()
        self.is_deleted = True
