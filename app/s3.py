import asyncio
from contextlib import suppress
from functools import lru_cache
from typing import TYPE_CHECKING

import boto3

from app.config import config

if TYPE_CHECKING:
    # 개발 의존성으로 선언한 S3 타입 정보다.
    # noinspection PyPackageRequirements
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_s3.type_defs import DeleteObjectRequestTypeDef


class S3StorageClient:
    def __init__(self, *, client: S3Client):
        self._client = client

    def close(self) -> None:
        self._client.close()

    async def upload(self, *, path: str, file: bytes, metadata: dict[str, str] | None = None) -> str:
        if metadata is None:
            metadata = {}

        upload = asyncio.create_task(
            asyncio.to_thread(
                self._client.put_object,
                Bucket=config.S3_BUCKET_NAME,
                Key=path,
                Body=file,
                Metadata=metadata,
            )
        )
        try:
            response = await asyncio.shield(upload)
        except asyncio.CancelledError:
            while not upload.done():
                with suppress(asyncio.CancelledError, Exception):
                    await asyncio.shield(upload)
            with suppress(Exception):
                upload.result()
            raise
        return response.get("VersionId", "null")

    async def download(self, *, path: str) -> bytes:
        return await asyncio.to_thread(self._download, path=path)

    def _download(self, *, path: str) -> bytes:
        response = self._client.get_object(Bucket=config.S3_BUCKET_NAME, Key=path)
        return response["Body"].read()

    async def delete(self, *, path: str, version_id: str | None = None) -> None:
        request: DeleteObjectRequestTypeDef = {"Bucket": config.S3_BUCKET_NAME, "Key": path}
        if version_id is not None:
            request["VersionId"] = version_id
        await asyncio.to_thread(self._client.delete_object, **request)

    def generate_presigned_url(self, *, path: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": config.S3_BUCKET_NAME, "Key": path},
            ExpiresIn=expires_in,
        )


@lru_cache(maxsize=1)
def get_s3() -> S3StorageClient:
    return S3StorageClient(
        client=boto3.client(
            "s3",
            endpoint_url=config.S3_ENDPOINT_URL,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
            region_name=config.S3_REGION,
        )
    )
