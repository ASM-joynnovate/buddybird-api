from uuid import uuid7

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import FileStatusEnum
from app.errors import FileSizeExceededError, InvalidProfilePhotoError, ParrotSaveUnavailableError
from app.models import File, Parrot, User
from app.s3 import UPLOAD_URL_EXPIRES_IN, S3StorageClient
from app.schemas.base import UploadDTO, UploadRequest
from app.schemas.parrots import CreateParrotRequest, ParrotDTO, ParrotPhotoDTO, UpdateParrotRequest
from app.services.users import MAX_PHOTO_BYTES, PHOTO_TYPES


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


@transactional(unavailable_error=ParrotSaveUnavailableError)
async def update_photo(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    parrot: Parrot,
    data: UploadRequest,
) -> UploadDTO:
    if data.content_type not in PHOTO_TYPES:
        raise InvalidProfilePhotoError

    if data.file_size > MAX_PHOTO_BYTES:
        raise FileSizeExceededError

    file_id = uuid7()

    photo_file = File(
        id=file_id,
        file_name="profile.jpg",
        file_path=f"user/{parrot.user_id}/parrot/{parrot.id}/{file_id}",
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
