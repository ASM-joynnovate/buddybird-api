from dataclasses import dataclass

from app.shared_kernel.domain.entities.file import File
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
