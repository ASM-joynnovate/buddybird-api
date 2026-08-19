from abc import ABC, abstractmethod
from uuid import UUID

from app.audio_capture.domain.entities.audio_segment import AudioSegment


class IAudioSegmentRepo(ABC):
    @abstractmethod
    async def get_by_capture_id(self, *, audio_capture_id: UUID) -> list[AudioSegment]:
        pass

    @abstractmethod
    async def get_labeled(self) -> list[AudioSegment]:
        pass

    @abstractmethod
    async def get_counts_by_capture_ids(self, *, audio_capture_ids: list[UUID]) -> dict[UUID, tuple[int, int]]:
        """캡처 id별 (전체 세그먼트 수, 라벨된 세그먼트 수)를 반환한다."""

    @abstractmethod
    async def get_by_id(self, *, audio_segment_id: UUID) -> AudioSegment | None:
        pass

    @abstractmethod
    async def save(self, *, audio_segment: AudioSegment) -> None:
        pass
