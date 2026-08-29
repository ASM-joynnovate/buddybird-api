from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.audio_capture.domain.entities.audio_capture import AudioCapture


class IAudioCaptureRepo(ABC):
    @abstractmethod
    async def get_by_id(self, *, audio_capture_id: UUID) -> AudioCapture | None:
        pass

    @abstractmethod
    async def get_list(
        self,
        *,
        firebase_anon_uid: str | None,
        word_label: str | None,
        label_option_ids: list[UUID],
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
        prev: int,
        limit: int,
    ) -> list[AudioCapture]:
        pass

    @abstractmethod
    async def get_count(
        self,
        *,
        firebase_anon_uid: str | None,
        word_label: str | None,
        label_option_ids: list[UUID],
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        pass

    @abstractmethod
    async def get_existing_client_capture_ids(
        self, *, firebase_anon_uid: str, client_capture_ids: list[str]
    ) -> set[str]:
        pass

    @abstractmethod
    async def detach_label_options(self, *, label_option_ids: list[UUID]) -> None:
        pass

    @abstractmethod
    async def save(self, *, audio_capture: AudioCapture) -> None:
        pass
