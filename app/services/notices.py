from datetime import UTC, datetime
from uuid import uuid7

from pydantic.experimental.missing_sentinel import MISSING
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import FileStatusEnum, LocaleEnum
from app.errors import (
    FileSizeExceededError,
    InvalidNoticeBodyError,
    InvalidNoticePeriodError,
    InvalidProfilePhotoError,
    NoticeSaveUnavailableError,
)
from app.models import File, I18n, Notice, NoticeImage, NoticeRead, User
from app.s3 import S3StorageClient
from app.schemas.base import I18nDTO, PageParams, UploadDTO, UploadRequest
from app.schemas.notices import BackofficeNoticeDTO, CreateNoticeRequest, NoticeDTO, NoticeImageDTO, UpdateNoticeRequest
from app.services.users import MAX_PHOTO_BYTES, PHOTO_TYPES


def build_notice_dto(
    notice: Notice, read_at: datetime | None, locale: LocaleEnum, storage: S3StorageClient
) -> NoticeDTO:
    return NoticeDTO(
        id=notice.id,
        title=notice.title_i18n.get_text(locale),
        body=notice.body_i18n.get_text(locale) if notice.body_i18n is not None else None,
        starts_at=notice.starts_at,
        ends_at=notice.ends_at,
        is_read=read_at is not None,
        images=[
            NoticeImageDTO(id=image.id, url=storage.generate_presigned_url(path=image.file.object_key))
            for image in notice.images
        ],
    )


def build_backoffice_notice_dto(notice: Notice, storage: S3StorageClient) -> BackofficeNoticeDTO:
    return BackofficeNoticeDTO(
        id=notice.id,
        title=I18nDTO(ko_kr=notice.title_i18n.ko_kr, en_us=notice.title_i18n.en_us),
        body=I18nDTO(ko_kr=notice.body_i18n.ko_kr, en_us=notice.body_i18n.en_us)
        if notice.body_i18n is not None
        else None,
        starts_at=notice.starts_at,
        ends_at=notice.ends_at,
        images=[
            NoticeImageDTO(id=image.id, url=storage.generate_presigned_url(path=image.file.object_key))
            for image in notice.images
        ],
    )


async def get_list(
    *, db: AsyncSession, user: User, locale: LocaleEnum, storage: S3StorageClient, query: PageParams
) -> tuple[list[NoticeDTO], int]:
    now = datetime.now(UTC)
    stmt = (
        select(Notice, NoticeRead.read_at)
        .outerjoin(NoticeRead, and_(NoticeRead.notice_id == Notice.id, NoticeRead.user_id == user.id))
        .where(Notice.starts_at <= now, or_(Notice.ends_at.is_(None), Notice.ends_at > now))
    )
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    rows = (
        await db.execute(
            stmt.order_by(Notice.starts_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return [build_notice_dto(notice, read_at, locale, storage) for notice, read_at in rows], total


async def get_detail(
    *, db: AsyncSession, user: User, locale: LocaleEnum, storage: S3StorageClient, notice: Notice
) -> NoticeDTO:
    read_at = await db.scalar(
        select(NoticeRead.read_at).where(NoticeRead.notice_id == notice.id, NoticeRead.user_id == user.id)
    )

    return build_notice_dto(notice, read_at, locale, storage)


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def mark_read(
    *, db: AsyncSession, user: User, locale: LocaleEnum, storage: S3StorageClient, notice: Notice
) -> NoticeDTO:
    await db.execute(
        insert(NoticeRead)
        .values(user_id=user.id, notice_id=notice.id, read_at=datetime.now(UTC))
        .on_conflict_do_nothing()
    )
    read_at = await db.scalar(
        select(NoticeRead.read_at).where(NoticeRead.notice_id == notice.id, NoticeRead.user_id == user.id)
    )

    return build_notice_dto(notice, read_at, locale, storage)


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def create(*, db: AsyncSession, storage: S3StorageClient, data: CreateNoticeRequest) -> BackofficeNoticeDTO:
    notice = Notice(
        title_i18n=I18n(ko_kr=data.title.ko_kr, en_us=data.title.en_us),
        body_i18n=I18n(ko_kr=data.body.ko_kr, en_us=data.body.en_us) if data.body is not None else None,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        is_deleted=False,
        images=[],
    )

    db.add(notice)
    await db.flush()

    return build_backoffice_notice_dto(notice, storage)


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def update(
    *, db: AsyncSession, storage: S3StorageClient, notice: Notice, data: UpdateNoticeRequest
) -> BackofficeNoticeDTO:
    if data.title is not MISSING:
        for name, value in data.title.model_dump(exclude_unset=True).items():
            setattr(notice.title_i18n, name, value)

    if data.body is None:
        notice.body_i18n = None
    elif data.body is not MISSING and notice.body_i18n is not None:
        for name, value in data.body.model_dump(exclude_unset=True).items():
            setattr(notice.body_i18n, name, value)
    elif data.body is not MISSING:
        if data.body.en_us is MISSING:
            raise InvalidNoticeBodyError

        notice.body_i18n = I18n(**data.body.model_dump(exclude_unset=True))

    for name, value in data.model_dump(exclude_unset=True, exclude={"title", "body"}).items():
        setattr(notice, name, value)

    if notice.ends_at is not None and notice.ends_at <= notice.starts_at:
        raise InvalidNoticePeriodError

    await db.flush()

    return build_backoffice_notice_dto(notice, storage)


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def delete(*, db: AsyncSession, notice: Notice) -> None:
    notice.is_deleted = True

    for image in notice.images:
        image.file.is_deleted = True

    await db.flush()


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def add_image(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    notice: Notice,
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
        file_path=f"notice/{notice.id}/{file_id}",
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


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def delete_image(
    *, db: AsyncSession, storage: S3StorageClient, notice: Notice, image: NoticeImage
) -> BackofficeNoticeDTO:
    notice.images.remove(image)
    image.file.is_deleted = True

    await db.delete(image)
    await db.flush()

    return build_backoffice_notice_dto(notice, storage)
