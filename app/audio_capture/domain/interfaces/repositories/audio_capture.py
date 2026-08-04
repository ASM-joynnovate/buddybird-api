from abc import ABC, abstractmethod
from uuid import UUID

from app.audio_capture.domain.entities.audio_capture import AudioCapture


class IAudioCaptureRepo(ABC):
    @abstractmethod
    async def get_by_id(self, *, audio_capture_id: UUID) -> AudioCapture | None:
        pass

    @abstractmethod
    async def get_existing_client_capture_ids(
        self, *, firebase_anon_uid: str, client_capture_ids: list[str]
    ) -> set[str]:
        pass

    @abstractmethod
    async def save(self, *, audio_capture: AudioCapture) -> None:
        pass
