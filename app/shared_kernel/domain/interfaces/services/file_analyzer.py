from abc import ABC, abstractmethod


class IFileAnalyzer(ABC):
    @abstractmethod
    def get_mime_type(self, *, file: bytes) -> str: ...

    @abstractmethod
    def get_file_size(self, *, file: bytes) -> int: ...
