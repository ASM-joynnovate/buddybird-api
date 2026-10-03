from uuid import uuid7

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import FileStatusEnum
from app.errors import FileSizeExceededError, InvalidProfilePhotoError, ParrotSaveUnavailableError
from app.models import File, Parrot, User
from app.s3 import S3StorageClient
from app.schemas.base import FileDTO, UploadDTO, UploadRequest
from app.schemas.parrots import CreateParrotRequest, ParrotDTO, UpdateParrotRequest
from app.services.users import MAX_PHOTO_BYTES, PHOTO_TYPES, get_uploading_photo_files


def build_parrot_dto(parrot: Parrot, uploading_photo_file: File | None, storage: S3StorageClient) -> ParrotDTO:
    photo = None
    uploading_photo = None

    if parrot.photo_file is not None:
        photo = FileDTO(
            url=storage.generate_presigned_url(path=parrot.photo_file.object_key),
            status=parrot.photo_file.status,
        )

    if uploading_photo_file is not None:
        uploading_photo = FileDTO(
            url=storage.generate_presigned_url(path=uploading_photo_file.object_key),
            status=uploading_photo_file.status,
        )

    return ParrotDTO(
        id=parrot.id,
        name=parrot.name,
        species=parrot.species,
        birthdate=parrot.birthdate,
        photo_file=photo,
        uploading_photo_file=uploading_photo,
    )


async def get_list(*, db: AsyncSession, user: User, storage: S3StorageClient) -> list[ParrotDTO]:
    parrots = (await db.scalars(select(Parrot).where(Parrot.user_id == user.id).order_by(Parrot.created_at))).all()
    uploading_photo_files = await get_uploading_photo_files(
        db=db,
        file_ids={parrot.uploading_photo_file_id for parrot in parrots if parrot.uploading_photo_file_id is not None},
    )

    return [
        build_parrot_dto(parrot, uploading_photo_files.get(parrot.uploading_photo_file_id), storage)
        for parrot in parrots
    ]


@transactional(unavailable_error=ParrotSaveUnavailableError)
async def create(*, db: AsyncSession, user: User, storage: S3StorageClient, data: CreateParrotRequest) -> ParrotDTO:
    parrot = Parrot(user_id=user.id, name=data.name, species=data.species, birthdate=data.birthdate, is_deleted=False)

    db.add(parrot)
    await db.flush()

    return build_parrot_dto(parrot, None, storage)


@transactional(unavailable_error=ParrotSaveUnavailableError)
async def update(*, db: AsyncSession, storage: S3StorageClient, parrot: Parrot, data: UpdateParrotRequest) -> ParrotDTO:
    for name, value in data.model_dump(exclude_unset=True).items():
        setattr(parrot, name, value)

    await db.flush()

    uploading_photo_files = await get_uploading_photo_files(
        db=db,
        file_ids={parrot.uploading_photo_file_id} if parrot.uploading_photo_file_id is not None else set(),
    )

    return build_parrot_dto(parrot, uploading_photo_files.get(parrot.uploading_photo_file_id), storage)


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

    parrot.uploading_photo_file_id = photo_file.id

    return storage.generate_presigned_upload(
        file_id=file_id,
        path=f"upload/{photo_file.object_key}",
        content_type=data.content_type,
        file_size=data.file_size,
    )


@transactional(unavailable_error=ParrotSaveUnavailableError)
async def delete_photo(*, db: AsyncSession, parrot: Parrot) -> None:
    old_file = parrot.photo_file

    if old_file is None:
        return

    parrot.photo_file = None
    old_file.is_deleted = True

    await db.flush()


async def get_detail(*, db: AsyncSession, parrot: Parrot, storage: S3StorageClient) -> ParrotDTO:
    uploading_photo_files = await get_uploading_photo_files(
        db=db,
        file_ids={parrot.uploading_photo_file_id} if parrot.uploading_photo_file_id is not None else set(),
    )

    return build_parrot_dto(parrot, uploading_photo_files.get(parrot.uploading_photo_file_id), storage)
