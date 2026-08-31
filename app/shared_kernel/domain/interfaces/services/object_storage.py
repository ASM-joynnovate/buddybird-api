from abc import ABC, abstractmethod


class IObjectStorageClient(ABC):
    @abstractmethod
    async def upload(self, *, path: str, file: bytes, metadata: dict[str, str] | None = None) -> None: ...

    @abstractmethod
    async def download(
        self,
        *,
        path: str,
    ) -> bytes: ...

    @abstractmethod
    async def delete(self, *, path: str) -> None: ...

    @abstractmethod
    async def generate_presigned_url(self, *, path: str, expires_in: int = 3600) -> str: ...
