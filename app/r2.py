import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING
from uuid import UUID

import boto3
from botocore.config import Config

from app.config import config
from app.schemas.base import UploadDTO

if TYPE_CHECKING:
    # noinspection PyPackageRequirements
    from mypy_boto3_s3 import S3Client

UPLOAD_URL_EXPIRES_IN = 300


class R2StorageClient:
    def __init__(self, *, client: S3Client):
        self._client = client

    def close(self) -> None:
        self._client.close()

    async def upload(
        self,
        *,
        path: str,
        file: bytes,
        metadata: dict[str, str] | None = None,
        content_type: str = "binary/octet-stream",
    ) -> None:
        if metadata is None:
            metadata = {}

        upload = asyncio.create_task(
            asyncio.to_thread(
                self._client.put_object,
                Bucket=config.STORAGE_BUCKET_NAME,
                Key=path,
                Body=file,
                Metadata=metadata,
                ContentType=content_type,
            )
        )
        try:
            await asyncio.shield(upload)
        except asyncio.CancelledError:
            while not upload.done():
                with suppress(asyncio.CancelledError, Exception):
                    await asyncio.shield(upload)
            with suppress(Exception):
                upload.result()
            raise

    async def download(self, *, path: str) -> bytes:
        return await asyncio.to_thread(self._download, path=path)

    def _download(self, *, path: str) -> bytes:
        response = self._client.get_object(Bucket=config.STORAGE_BUCKET_NAME, Key=path)
        return response["Body"].read()

    async def delete(self, *, path: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=config.STORAGE_BUCKET_NAME, Key=path)

    def generate_presigned_url(self, *, path: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": config.STORAGE_BUCKET_NAME, "Key": path},
            ExpiresIn=expires_in,
        )

    def generate_presigned_upload(self, *, file_id: UUID, path: str, content_type: str, file_size: int) -> UploadDTO:
        url = self._client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": config.STORAGE_BUCKET_NAME,
                "Key": path,
                "ContentType": content_type,
                "ContentLength": file_size,
            },
            ExpiresIn=UPLOAD_URL_EXPIRES_IN,
        )

        return UploadDTO(
            file_id=file_id,
            url=url,
            headers={"Content-Type": content_type},
            expires_in=UPLOAD_URL_EXPIRES_IN,
        )


r2 = R2StorageClient(
    client=boto3.client(
        "s3",
        endpoint_url=config.STORAGE_ENDPOINT_URL,
        aws_access_key_id=config.STORAGE_ACCESS_KEY,
        aws_secret_access_key=config.STORAGE_SECRET_KEY,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )
)


async def get_r2() -> R2StorageClient:
    return r2
