from abc import ABC, abstractmethod


class IObjectStorageClient(ABC):
    @abstractmethod
    async def upload(self, *, path: str, file: bytes, metadata: dict[str, str] | None = None) -> None:
        pass

    @abstractmethod
    async def download(
        self,
        *,
        path: str,
    ) -> bytes:
        pass

    @abstractmethod
    async def delete(self, *, path: str) -> None:
        pass

    @abstractmethod
    async def generate_presigned_url(self, *, path: str, expires_in: int = 3600) -> str:
        pass
