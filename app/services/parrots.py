import asyncio
from uuid import uuid7

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import ParrotSaveUnavailableError, ProfilePhotoServiceUnavailableError
from app.models import File, Parrot, User
from app.s3 import S3StorageClient
from app.schemas.parrots import CreateParrotRequest, ParrotDTO, ParrotPhotoDTO, UpdateParrotRequest
from app.services.users import delete_uploaded_photo, prepare_uploaded_photo


def build_parrot_dto(parrot: Parrot, storage: S3StorageClient) -> ParrotDTO:
    photo = None

    if parrot.photo_file is not None:
        photo = ParrotPhotoDTO(url=storage.generate_presigned_url(path=parrot.photo_file.object_key))

    return ParrotDTO(id=parrot.id, name=parrot.name, species=parrot.species, birthdate=parrot.birthdate, photo=photo)


async def get_list(*, db: AsyncSession, user: User, storage: S3StorageClient) -> list[ParrotDTO]:
    parrots = (await db.scalars(select(Parrot).where(Parrot.user_id == user.id).order_by(Parrot.created_at))).all()

    return [build_parrot_dto(parrot, storage) for parrot in parrots]


@transactional(unavailable_error=ParrotSaveUnavailableError)
async def create(*, db: AsyncSession, user: User, storage: S3StorageClient, data: CreateParrotRequest) -> ParrotDTO:
    parrot = Parrot(user_id=user.id, name=data.name, species=data.species, birthdate=data.birthdate, is_deleted=False)

    db.add(parrot)
    await db.flush()

    return build_parrot_dto(parrot, storage)


@transactional(unavailable_error=ParrotSaveUnavailableError)
async def update(*, db: AsyncSession, storage: S3StorageClient, parrot: Parrot, data: UpdateParrotRequest) -> ParrotDTO:
    changes = data.model_dump(exclude_unset=True)

    if "name" in changes:
        parrot.name = changes["name"]

    if "species" in changes:
        parrot.species = changes["species"]

    if "birthdate" in changes:
        parrot.birthdate = changes["birthdate"]

    await db.flush()

    return build_parrot_dto(parrot, storage)


@transactional(unavailable_error=ParrotSaveUnavailableError)
async def delete(*, db: AsyncSession, parrot: Parrot) -> None:
    parrot.is_deleted = True

    if parrot.photo_file is not None:
        parrot.photo_file.is_deleted = True

    await db.flush()


async def update_photo(*, db: AsyncSession, storage: S3StorageClient, parrot: Parrot, file: UploadFile) -> ParrotDTO:
    content = await prepare_uploaded_photo(file)

    file_id = uuid7()
    file_path = f"user/{parrot.user_id}/parrot/{parrot.id}/{file_id}"
    path = f"{file_path}/profile.jpg"

    try:
        version_id = await storage.upload(path=path, file=content)
    except (BotoCoreError, ClientError, OSError, TimeoutError) as exc:
        raise ProfilePhotoServiceUnavailableError from exc

    photo_file = File(
        id=file_id,
        file_name="profile.jpg",
        file_path=file_path,
        file_size=len(content),
        file_type="image/jpeg",
        is_deleted=False,
    )

    try:
        await save_photo(db=db, parrot=parrot, photo_file=photo_file)
    except Exception, asyncio.CancelledError:
        await delete_uploaded_photo(storage=storage, path=path, version_id=version_id)

        raise

    return build_parrot_dto(parrot, storage)


@transactional(unavailable_error=ParrotSaveUnavailableError)
async def save_photo(*, db: AsyncSession, parrot: Parrot, photo_file: File) -> None:
    old_file = parrot.photo_file

    db.add(photo_file)
    parrot.photo_file = photo_file

    if old_file is not None:
        old_file.is_deleted = True

    await db.flush()


@transactional(unavailable_error=ParrotSaveUnavailableError)
async def delete_photo(*, db: AsyncSession, parrot: Parrot) -> None:
    old_file = parrot.photo_file

    if old_file is None:
        return

    parrot.photo_file = None
    old_file.is_deleted = True

    await db.flush()


def get_detail(*, parrot: Parrot, storage: S3StorageClient) -> ParrotDTO:
    return build_parrot_dto(parrot, storage)
