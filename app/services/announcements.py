from datetime import UTC, datetime
from uuid import uuid7

from pydantic.experimental.missing_sentinel import MISSING
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import FileStatusEnum, LocaleEnum
from app.errors import (
    AnnouncementSaveUnavailableError,
    FileSizeExceededError,
    InvalidAnnouncementBodyError,
    InvalidAnnouncementPeriodError,
    InvalidProfilePhotoError,
)
from app.models import Announcement, AnnouncementImage, AnnouncementRead, File, I18n, User
from app.s3 import S3StorageClient
from app.schemas.announcements import (
    AnnouncementDTO,
    AnnouncementImageDTO,
    BackofficeAnnouncementDTO,
    CreateAnnouncementRequest,
    UpdateAnnouncementRequest,
)
from app.schemas.base import I18nDTO, PageParams, UploadDTO, UploadRequest
from app.services.users import MAX_PHOTO_BYTES, PHOTO_TYPES


def build_announcement_dto(
    announcement: Announcement, read_at: datetime | None, locale: LocaleEnum, storage: S3StorageClient
) -> AnnouncementDTO:
    return AnnouncementDTO(
        id=announcement.id,
        title=announcement.title_i18n.get_text(locale),
        body=announcement.body_i18n.get_text(locale) if announcement.body_i18n is not None else None,
        starts_at=announcement.starts_at,
        ends_at=announcement.ends_at,
        is_read=read_at is not None,
        images=[
            AnnouncementImageDTO(id=image.id, url=storage.generate_presigned_url(path=image.file.object_key))
            for image in announcement.images
        ],
    )


def build_backoffice_announcement_dto(
    announcement: Announcement, storage: S3StorageClient
) -> BackofficeAnnouncementDTO:
    return BackofficeAnnouncementDTO(
        id=announcement.id,
        title=I18nDTO(ko_kr=announcement.title_i18n.ko_kr, en_us=announcement.title_i18n.en_us),
        body=I18nDTO(ko_kr=announcement.body_i18n.ko_kr, en_us=announcement.body_i18n.en_us)
        if announcement.body_i18n is not None
        else None,
        starts_at=announcement.starts_at,
        ends_at=announcement.ends_at,
        push_enabled=announcement.push_enabled,
        push_local_time=announcement.push_local_time,
        push_prepared_at=announcement.push_prepared_at,
        images=[
            AnnouncementImageDTO(id=image.id, url=storage.generate_presigned_url(path=image.file.object_key))
            for image in announcement.images
        ],
    )


async def get_list(
    *, db: AsyncSession, user: User, locale: LocaleEnum, storage: S3StorageClient, query: PageParams
) -> tuple[list[AnnouncementDTO], int]:
    now = datetime.now(UTC)
    stmt = (
        select(Announcement, AnnouncementRead.read_at)
        .outerjoin(
            AnnouncementRead,
            and_(AnnouncementRead.announcement_id == Announcement.id, AnnouncementRead.user_id == user.id),
        )
        .where(Announcement.starts_at <= now, or_(Announcement.ends_at.is_(None), Announcement.ends_at > now))
    )
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    rows = (
        await db.execute(
            stmt.order_by(Announcement.starts_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return [build_announcement_dto(announcement, read_at, locale, storage) for announcement, read_at in rows], total


async def get_detail(
    *, db: AsyncSession, user: User, locale: LocaleEnum, storage: S3StorageClient, announcement: Announcement
) -> AnnouncementDTO:
    read_at = await db.scalar(
        select(AnnouncementRead.read_at).where(
            AnnouncementRead.announcement_id == announcement.id, AnnouncementRead.user_id == user.id
        )
    )

    return build_announcement_dto(announcement, read_at, locale, storage)


async def get_backoffice_list(
    *, db: AsyncSession, storage: S3StorageClient, query: PageParams
) -> tuple[list[BackofficeAnnouncementDTO], int]:
    stmt = select(Announcement)
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    announcements = (
        await db.scalars(
            stmt.order_by(Announcement.starts_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return [build_backoffice_announcement_dto(announcement, storage) for announcement in announcements], total


@transactional(unavailable_error=AnnouncementSaveUnavailableError)
async def mark_read(
    *, db: AsyncSession, user: User, locale: LocaleEnum, storage: S3StorageClient, announcement: Announcement
) -> AnnouncementDTO:
    await db.execute(
        insert(AnnouncementRead)
        .values(user_id=user.id, announcement_id=announcement.id, read_at=datetime.now(UTC))
        .on_conflict_do_nothing()
    )
    read_at = await db.scalar(
        select(AnnouncementRead.read_at).where(
            AnnouncementRead.announcement_id == announcement.id, AnnouncementRead.user_id == user.id
        )
    )

    return build_announcement_dto(announcement, read_at, locale, storage)


@transactional(unavailable_error=AnnouncementSaveUnavailableError)
async def create(
    *, db: AsyncSession, storage: S3StorageClient, data: CreateAnnouncementRequest
) -> BackofficeAnnouncementDTO:
    announcement = Announcement(
        title_i18n=I18n(ko_kr=data.title.ko_kr, en_us=data.title.en_us),
        body_i18n=I18n(ko_kr=data.body.ko_kr, en_us=data.body.en_us) if data.body is not None else None,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        push_enabled=data.push_enabled,
        push_local_time=data.push_local_time,
        is_deleted=False,
        images=[],
    )

    db.add(announcement)
    await db.flush()

    return build_backoffice_announcement_dto(announcement, storage)


@transactional(unavailable_error=AnnouncementSaveUnavailableError)
async def update(
    *, db: AsyncSession, storage: S3StorageClient, announcement: Announcement, data: UpdateAnnouncementRequest
) -> BackofficeAnnouncementDTO:
    if data.title is not MISSING:
        for name, value in data.title.model_dump(exclude_unset=True).items():
            setattr(announcement.title_i18n, name, value)

    if data.body is None:
        announcement.body_i18n = None
    elif data.body is not MISSING and announcement.body_i18n is not None:
        for name, value in data.body.model_dump(exclude_unset=True).items():
            setattr(announcement.body_i18n, name, value)
    elif data.body is not MISSING:
        if data.body.en_us is MISSING:
            raise InvalidAnnouncementBodyError

        announcement.body_i18n = I18n(**data.body.model_dump(exclude_unset=True))

    for name, value in data.model_dump(exclude_unset=True, exclude={"title", "body"}).items():
        setattr(announcement, name, value)

    if announcement.ends_at is not None and announcement.ends_at <= announcement.starts_at:
        raise InvalidAnnouncementPeriodError

    await db.flush()

    return build_backoffice_announcement_dto(announcement, storage)


@transactional(unavailable_error=AnnouncementSaveUnavailableError)
async def delete(*, db: AsyncSession, announcement: Announcement) -> None:
    announcement.is_deleted = True

    for image in announcement.images:
        image.file.is_deleted = True

    await db.flush()


@transactional(unavailable_error=AnnouncementSaveUnavailableError)
async def add_image(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    announcement: Announcement,
    data: UploadRequest,
) -> UploadDTO:
    if data.content_type not in PHOTO_TYPES:
        raise InvalidProfilePhotoError

    if data.file_size > MAX_PHOTO_BYTES:
        raise FileSizeExceededError

    file_id = uuid7()

    image_file = File(
        id=file_id,
        file_name="image.jpg",
        file_path=f"announcement/{announcement.id}/{file_id}",
        file_size=data.file_size,
        file_type="image/jpeg",
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )

    db.add(image_file)

    await db.flush()

    return storage.generate_presigned_upload(
        file_id=file_id,
        path=f"upload/{image_file.object_key}",
        content_type=data.content_type,
        file_size=data.file_size,
    )


@transactional(unavailable_error=AnnouncementSaveUnavailableError)
async def delete_image(
    *, db: AsyncSession, storage: S3StorageClient, announcement: Announcement, image: AnnouncementImage
) -> BackofficeAnnouncementDTO:
    announcement.images.remove(image)
    image.file.is_deleted = True

    await db.delete(image)
    await db.flush()

    return build_backoffice_announcement_dto(announcement, storage)
