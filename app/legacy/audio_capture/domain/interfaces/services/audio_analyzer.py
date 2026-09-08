from abc import ABC, abstractmethod


class IAudioAnalyzer(ABC):
    @abstractmethod
    def trim(self, *, file: bytes, start_ms: int, end_ms: int) -> bytes: ...
