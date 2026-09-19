import asyncio
import io
import logging
from urllib.parse import urlsplit
from uuid import uuid7

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import FileStatusEnum
from app.errors import (
    AuthenticationError,
    DuplicateNicknameError,
    FileSizeExceededError,
    InvalidProfilePhotoError,
    UserSaveUnavailableError,
)
from app.models import File, User
from app.oauth.base import http_client
from app.s3 import UPLOAD_URL_EXPIRES_IN, S3StorageClient
from app.schemas.base import UploadDTO, UploadRequest
from app.schemas.users import ProfilePhotoDTO, UpdateUserRequest, UserDTO

logger = logging.getLogger(__name__)

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_PHOTO_PIXELS = 20_000_000
PHOTO_TYPES = {"image/jpeg", "image/png"}
SOCIAL_PHOTO_TYPES = {"image/jpeg": "profile.jpg", "image/png": "profile.png", "image/webp": "profile.webp"}
SOCIAL_PHOTO_HOSTS = {
    "google": {"googleusercontent.com", "lh3.googleusercontent.com"},
    "kakao": {"k.kakaocdn.net", "t1.kakaocdn.net", "t1.daumcdn.net"},
}


async def download_social_photo(*, url: str, provider: str) -> tuple[bytes, str, str] | None:
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname or ""
        allowed_hosts = SOCIAL_PHOTO_HOSTS.get(provider, ())
        disallowed = (
            parsed.scheme != "https"
            or hostname not in allowed_hosts
            or parsed.port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        )

        if disallowed:
            return None

        async with asyncio.timeout(10), http_client.stream("GET", url) as response:
            response.raise_for_status()

            file_type = response.headers.get("content-type", "").partition(";")[0].lower()
            file_name = SOCIAL_PHOTO_TYPES.get(file_type)

            if file_name is None or int(response.headers.get("content-length", "0")) > MAX_PHOTO_BYTES:
                return None

            content = bytearray()

            async for chunk in response.aiter_bytes(64 * 1024):
                content.extend(chunk)

                if len(content) > MAX_PHOTO_BYTES:
                    return None
    except httpx.HTTPError, OSError, TimeoutError, ValueError:
        return None

    if not content:
        return None

    return bytes(content), file_name, file_type


async def prepare_uploaded_photo(content: bytes) -> bytes:
    def transform() -> bytes:
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in {"JPEG", "PNG"} or source.width * source.height > MAX_PHOTO_PIXELS:
                raise ValueError

            image = ImageOps.exif_transpose(source)

            if "A" in image.getbands() or (image.mode == "P" and "transparency" in image.info):
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")

            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85)

            return output.getvalue()

    try:
        return await asyncio.to_thread(transform)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidProfilePhotoError from exc


async def delete_uploaded_photo(*, storage: S3StorageClient, path: str, version_id: str) -> None:
    try:
        await storage.delete(path=path, version_id=version_id)
    except Exception:
        logger.exception("업로드된 프로필 사진 정리 실패")


async def get_profile(*, user: User, storage: S3StorageClient) -> UserDTO:
    photo = None

    if user.photo_file is not None:
        photo = ProfilePhotoDTO(url=storage.generate_presigned_url(path=user.photo_file.object_key))

    return UserDTO(id=user.id, email=user.email, nickname=user.nickname, photo=photo)


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_profile(*, db: AsyncSession, user: User, data: UpdateUserRequest) -> None:
    changes = data.model_dump(exclude_unset=True)

    if "nickname" not in changes:
        return

    if user.is_deleted:
        raise AuthenticationError

    user.nickname = changes["nickname"]

    try:
        await db.flush()
    except IntegrityError as exc:
        raise DuplicateNicknameError from exc


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_photo(*, db: AsyncSession, storage: S3StorageClient, user: User, data: UploadRequest) -> UploadDTO:
    if user.is_deleted:
        raise AuthenticationError

    if data.content_type not in PHOTO_TYPES:
        raise InvalidProfilePhotoError

    if data.file_size > MAX_PHOTO_BYTES:
        raise FileSizeExceededError

    file_id = uuid7()

    photo_file = File(
        id=file_id,
        file_name="profile.jpg",
        file_path=f"user/{user.id}/profile/{file_id}",
        file_size=data.file_size,
        file_type="image/jpeg",
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )

    db.add(photo_file)

    await db.flush()

    return UploadDTO(
        file_id=file_id,
        url=storage.generate_presigned_upload_url(
            path=f"upload/{photo_file.object_key}",
            file_type=data.content_type,
            file_size=data.file_size,
        ),
        headers={"Content-Type": data.content_type},
        expires_in=UPLOAD_URL_EXPIRES_IN,
    )


@transactional(unavailable_error=UserSaveUnavailableError)
async def delete_photo(*, db: AsyncSession, user: User) -> None:
    if user.is_deleted:
        raise AuthenticationError

    old_file = user.photo_file

    if old_file is None:
        return

    user.photo_file = None
    old_file.is_deleted = True

    await db.flush()
