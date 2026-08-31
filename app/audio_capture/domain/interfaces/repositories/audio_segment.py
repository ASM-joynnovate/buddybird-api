from abc import ABC, abstractmethod
from uuid import UUID

from app.audio_capture.domain.entities.audio_segment import AudioSegment


class IAudioSegmentRepo(ABC):
    @abstractmethod
    async def get_by_capture_id(self, *, audio_capture_id: UUID) -> list[AudioSegment]: ...

    @abstractmethod
    async def get_labeled(self, *, audio_capture_label_option_ids: list[UUID] | None) -> list[AudioSegment]: ...

    # 캡처 ID별 전체, 라벨 지정, 메모 존재 세그먼트 수 반환
    @abstractmethod
    async def get_counts_by_capture_ids(self, *, audio_capture_ids: list[UUID]) -> dict[UUID, tuple[int, int, int]]: ...

    @abstractmethod
    async def get_by_id(self, *, audio_segment_id: UUID) -> AudioSegment | None: ...

    @abstractmethod
    async def detach_label_options(self, *, label_option_ids: list[UUID]) -> None: ...

    @abstractmethod
    async def save(self, *, audio_segment: AudioSegment) -> None: ...
