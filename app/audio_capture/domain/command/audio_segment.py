from dataclasses import dataclass
from uuid import UUID

from app.audio_capture.domain.value_objects import AudioSegmentRange
from app.shared_kernel.domain.command.file import AssignFileCommand


@dataclass
class CreateAudioSegmentCommand:
    audio_capture_id: UUID
    firebase_anon_uid: str
    range: AudioSegmentRange
    audio_file: AssignFileCommand


@dataclass
class TrimAudioSegmentCommand:
    range: AudioSegmentRange
    audio_file: AssignFileCommand


@dataclass
class AssignAudioSegmentLabelCommand:
    label_option_id: UUID
