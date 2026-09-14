import asyncio
import io
import logging
from contextlib import suppress
from urllib.parse import urlsplit
from uuid import UUID, uuid7

import httpx
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db import session_factory
from app.errors import (
    DuplicateNicknameError,
    FileSizeExceededError,
    InvalidProfilePhotoError,
    ProfilePhotoServiceUnavailableError,
    ResourceNotFoundError,
    UserSaveUnavailableError,
)
from app.models import File, User
from app.s3 import S3StorageClient
from app.schemas import ProfilePhotoDTO, UpdateUserRequest, UserDTO

logger = logging.getLogger(__name__)

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_PHOTO_PIXELS = 20_000_000
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
        if (
            parsed.scheme != "https"
            or hostname not in allowed_hosts
            or parsed.port not in {None, 443}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            return None
        async with (
            asyncio.timeout(10),
            httpx.AsyncClient(timeout=5, follow_redirects=False) as client,
            client.stream("GET", url) as response,
        ):
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
        return (bytes(content), file_name, file_type) if content else None
    except httpx.HTTPError, OSError, TimeoutError, ValueError:
        return None


async def prepare_uploaded_photo(file: UploadFile) -> bytes:
    content = await file.read(MAX_PHOTO_BYTES + 1)
    if len(content) > MAX_PHOTO_BYTES:
        raise FileSizeExceededError

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


async def delete_uploaded_photo(*, storage: S3StorageClient, path: str) -> None:
    try:
        await storage.delete(path=path)
    except Exception:
        logger.exception("업로드된 프로필 사진 정리 실패")


async def rollback_or_unavailable(*, db) -> None:
    try:
        await db.rollback()
    except SQLAlchemyError as exc:
        raise UserSaveUnavailableError from exc


async def get_profile(*, user_id: UUID, db, storage: S3StorageClient) -> UserDTO:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise ResourceNotFoundError
    photo = None
    if user.photo_file is not None:
        photo = ProfilePhotoDTO(
            url=storage.generate_presigned_url(path=f"{user.photo_file.file_path}/{user.photo_file.file_name}")
        )
    return UserDTO(id=user.id, email=user.email, nickname=user.nickname, photo=photo)


async def update_profile(*, user_id: UUID, data: UpdateUserRequest, db) -> None:
    changes = data.model_dump(exclude_unset=True)
    if "nickname" not in changes:
        return
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise ResourceNotFoundError
    user.nickname = changes["nickname"]
    try:
        await db.flush()
    except IntegrityError as exc:
        await rollback_or_unavailable(db=db)
        raise DuplicateNicknameError from exc
    except SQLAlchemyError as exc:
        await rollback_or_unavailable(db=db)
        raise UserSaveUnavailableError from exc
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        with suppress(SQLAlchemyError):
            await db.rollback()
        async with session_factory() as check_db:
            saved = (
                await check_db.execute(
                    select(User.id, User.nickname).where(User.id == user_id).execution_options(use_writer=True)
                )
            ).one_or_none()
        if saved is not None and saved.nickname == changes["nickname"]:
            return
        raise UserSaveUnavailableError from exc


async def update_photo(*, user_id: UUID, file: UploadFile, db, storage: S3StorageClient) -> None:
    content = await prepare_uploaded_photo(file)
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise ResourceNotFoundError
    old_file = user.photo_file
    file_id = uuid7()
    file_path = f"user/{user_id}/profile/{file_id}"
    path = f"{file_path}/profile.jpg"
    try:
        await storage.upload(path=path, file=content)
    except (BotoCoreError, ClientError, OSError, TimeoutError) as exc:
        raise ProfilePhotoServiceUnavailableError from exc

    new_file = File(
        id=file_id,
        file_name="profile.jpg",
        file_path=file_path,
        file_size=len(content),
        file_type="image/jpeg",
        is_deleted=False,
    )
    db.add(new_file)
    user.photo_file = new_file
    if old_file is not None:
        old_file.is_deleted = True
    try:
        await db.flush()
    except SQLAlchemyError as exc:
        await rollback_or_unavailable(db=db)
        await delete_uploaded_photo(storage=storage, path=path)
        raise UserSaveUnavailableError from exc
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        with suppress(SQLAlchemyError):
            await db.rollback()
        async with session_factory() as check_db:
            saved = (
                await check_db.execute(
                    select(User.id, User.photo_file_id).where(User.id == user_id).execution_options(use_writer=True)
                )
            ).one_or_none()
        if saved is not None and saved.photo_file_id == file_id:
            return
        raise UserSaveUnavailableError from exc


async def delete_photo(*, user_id: UUID, db) -> None:
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise ResourceNotFoundError
    old_file = user.photo_file
    if old_file is None:
        return
    user.photo_file = None
    old_file.is_deleted = True
    try:
        await db.flush()
    except SQLAlchemyError as exc:
        await rollback_or_unavailable(db=db)
        raise UserSaveUnavailableError from exc
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        with suppress(SQLAlchemyError):
            await db.rollback()
        async with session_factory() as check_db:
            saved = (
                await check_db.execute(
                    select(User.id, User.photo_file_id).where(User.id == user_id).execution_options(use_writer=True)
                )
            ).one_or_none()
        if saved is not None and saved.photo_file_id is None:
            return
        raise UserSaveUnavailableError from exc
