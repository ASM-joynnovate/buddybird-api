import asyncio

import boto3

from app.shared_kernel.domain.interfaces.object_storage import IObjectStorageClient
from core.config import config


class S3StorageClient(IObjectStorageClient):
    def __init__(self):
        self._client = boto3.client(
            service_name="s3",
            endpoint_url=config.S3_ENDPOINT_URL,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
            region_name=config.S3_REGION,
        )

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
