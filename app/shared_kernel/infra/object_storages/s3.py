import asyncio

from app.shared_kernel.domain.interfaces.services import IObjectStorageClient
from core.config import config


class S3StorageClient(IObjectStorageClient):
    def __init__(self, *, client):
        self._client = client

    async def upload(self, *, path: str, file: bytes, metadata: dict[str, str] | None = None) -> None:
        if metadata is None:
            metadata = {}

        await asyncio.to_thread(
            self._client.put_object,
            Bucket=config.S3_BUCKET_NAME,
            Key=path,
            Body=file,
            Metadata=metadata,
        )

    async def download(self, *, path: str) -> bytes:
        return await asyncio.to_thread(self._download, path=path)

    def _download(self, *, path: str) -> bytes:
        response = self._client.get_object(Bucket=config.S3_BUCKET_NAME, Key=path)
        return response["Body"].read()

    async def delete(self, *, path: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=config.S3_BUCKET_NAME,
            Key=path,
        )

    async def generate_presigned_url(self, *, path: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": config.S3_BUCKET_NAME, "Key": path},
            ExpiresIn=expires_in,
        )
