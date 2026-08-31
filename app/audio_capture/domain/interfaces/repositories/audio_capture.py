from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.audio_capture.domain.entities.audio_capture import AudioCapture


class IAudioCaptureRepo(ABC):
    @abstractmethod
    async def get_by_id(self, *, audio_capture_id: UUID) -> AudioCapture | None: ...

    @abstractmethod
    async def get_list(
        self,
        *,
        user_id: str | None,
        word_label: str | None,
        label_option_ids: list[UUID] | None,
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
        prev: int,
        limit: int,
    ) -> list[AudioCapture]: ...

    @abstractmethod
    async def get_count(
        self,
        *,
        user_id: str | None,
        word_label: str | None,
        label_option_ids: list[UUID] | None,
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int: ...

    @abstractmethod
    async def get_existing_client_capture_ids(self, *, user_id: str, client_capture_ids: list[str]) -> set[str]: ...

    @abstractmethod
    async def detach_label_options(self, *, label_option_ids: list[UUID]) -> None: ...

    @abstractmethod
    async def get_by_audio_file_path(self, *, file_path: str, file_name: str) -> AudioCapture | None: ...

    @abstractmethod
    async def save(self, *, audio_capture: AudioCapture) -> None: ...
