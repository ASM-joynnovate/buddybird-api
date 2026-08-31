from dataclasses import dataclass

from app.shared_kernel.domain.commands import AssignFileCommand


@dataclass(frozen=True)
class CreateWordCommand:
    label: str
    firebase_anon_uid: str
    client_word_id: str
    audio_file: AssignFileCommand
    device_platform: str | None
    device_os_version: str | None
    device_model: str | None
