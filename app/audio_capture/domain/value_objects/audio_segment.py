from dataclasses import dataclass

from app.audio_capture.domain.errors import InvalidAudioSegmentRangeError


@dataclass(frozen=True)
class AudioSegmentRange:
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        if self.end_ms <= self.start_ms:
            raise InvalidAudioSegmentRangeError

    def __composite_values__(self) -> tuple[int, int]:
        return self.start_ms, self.end_ms
