from dataclasses import dataclass

from app.shared_kernel.domain.command.file import AssignFileCommand


@dataclass
class CreateWordCommand:
    label: str
    firebase_anon_uid: str
    audio_file: AssignFileCommand
    device_platform: str | None
    device_os_version: str | None
    device_model: str | None
