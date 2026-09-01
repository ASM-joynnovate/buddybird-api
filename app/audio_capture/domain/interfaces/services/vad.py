from abc import ABC, abstractmethod


class IVadService(ABC):
    @abstractmethod
    def detect(self, *, file: bytes) -> list[tuple[int, int]]: ...
