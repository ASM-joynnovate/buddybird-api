from dataclasses import dataclass
from uuid import UUID

from app.audio_capture.domain.value_objects import AudioSegmentRange
from app.shared_kernel.domain.commands import AssignFileCommand


@dataclass(frozen=True)
class CreateAudioSegmentCommand:
    audio_capture_id: UUID
    firebase_anon_uid: str
    range: AudioSegmentRange
    audio_file: AssignFileCommand


@dataclass(frozen=True)
class TrimAudioSegmentCommand:
    range: AudioSegmentRange
    audio_file: AssignFileCommand


@dataclass(frozen=True)
class AssignAudioSegmentLabelCommand:
    label_option_id: UUID


@dataclass(frozen=True)
class UpdateAudioSegmentMemoCommand:
    memo: str | None
