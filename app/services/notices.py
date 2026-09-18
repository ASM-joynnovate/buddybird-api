import asyncio
from datetime import UTC, datetime
from uuid import uuid7

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import InvalidNoticePeriodError, NoticeImageServiceUnavailableError, NoticeSaveUnavailableError
from app.models import File, Notice, NoticeImage, NoticeRead, User
from app.s3 import S3StorageClient
from app.schemas.base import PageParams
from app.schemas.notices import CreateNoticeRequest, NoticeDTO, NoticeImageDTO, UpdateNoticeRequest
from app.services.users import delete_uploaded_photo, prepare_uploaded_photo


def build_notice_dto(notice: Notice, read_at: datetime | None, storage: S3StorageClient) -> NoticeDTO:
    return NoticeDTO(
        id=notice.id,
        title=notice.title,
        body=notice.body,
        starts_at=notice.starts_at,
        ends_at=notice.ends_at,
        is_read=read_at is not None,
        images=[
            NoticeImageDTO(id=image.id, url=storage.generate_presigned_url(path=image.file.object_key))
            for image in notice.images
        ],
    )


async def get_list(
    *, db: AsyncSession, user: User, storage: S3StorageClient, query: PageParams
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

    return [build_notice_dto(notice, read_at, storage) for notice, read_at in rows], total


async def get_detail(*, db: AsyncSession, user: User, storage: S3StorageClient, notice: Notice) -> NoticeDTO:
    read_at = await db.scalar(
        select(NoticeRead.read_at).where(NoticeRead.notice_id == notice.id, NoticeRead.user_id == user.id)
    )

    return build_notice_dto(notice, read_at, storage)


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def mark_read(*, db: AsyncSession, user: User, storage: S3StorageClient, notice: Notice) -> NoticeDTO:
    await db.execute(
        insert(NoticeRead)
        .values(user_id=user.id, notice_id=notice.id, read_at=datetime.now(UTC))
        .on_conflict_do_nothing()
    )
    read_at = await db.scalar(
        select(NoticeRead.read_at).where(NoticeRead.notice_id == notice.id, NoticeRead.user_id == user.id)
    )

    return build_notice_dto(notice, read_at, storage)


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def create(*, db: AsyncSession, storage: S3StorageClient, data: CreateNoticeRequest) -> NoticeDTO:
    notice = Notice(
        title=data.title,
        body=data.body,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        is_deleted=False,
        images=[],
    )

    db.add(notice)
    await db.flush()

    return build_notice_dto(notice, None, storage)


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def update(*, db: AsyncSession, storage: S3StorageClient, notice: Notice, data: UpdateNoticeRequest) -> NoticeDTO:
    changes = data.model_dump(exclude_unset=True)

    if "title" in changes:
        notice.title = changes["title"]

    if "body" in changes:
        notice.body = changes["body"]

    if "starts_at" in changes:
        notice.starts_at = changes["starts_at"]

    if "ends_at" in changes:
        notice.ends_at = changes["ends_at"]

    if notice.ends_at is not None and notice.ends_at <= notice.starts_at:
        raise InvalidNoticePeriodError

    await db.flush()

    return build_notice_dto(notice, None, storage)


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def delete(*, db: AsyncSession, notice: Notice) -> None:
    notice.is_deleted = True

    for image in notice.images:
        image.file.is_deleted = True

    await db.flush()


async def add_image(*, db: AsyncSession, storage: S3StorageClient, notice: Notice, file: UploadFile) -> NoticeDTO:
    content = await prepare_uploaded_photo(file)

    file_id = uuid7()
    file_path = f"notice/{notice.id}/{file_id}"
    path = f"{file_path}/image.jpg"

    try:
        version_id = await storage.upload(path=path, file=content)
    except (BotoCoreError, ClientError, OSError, TimeoutError) as exc:
        raise NoticeImageServiceUnavailableError from exc

    image_file = File(
        id=file_id,
        file_name="image.jpg",
        file_path=file_path,
        file_size=len(content),
        file_type="image/jpeg",
        is_deleted=False,
    )

    try:
        await save_image(db=db, notice=notice, image_file=image_file)
    except Exception, asyncio.CancelledError:
        await delete_uploaded_photo(storage=storage, path=path, version_id=version_id)

        raise

    return build_notice_dto(notice, None, storage)


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def save_image(*, db: AsyncSession, notice: Notice, image_file: File) -> None:
    display_order = max((image.display_order for image in notice.images), default=-1) + 1

    db.add(image_file)
    notice.images.append(NoticeImage(file=image_file, display_order=display_order))

    await db.flush()


@transactional(unavailable_error=NoticeSaveUnavailableError)
async def delete_image(*, db: AsyncSession, storage: S3StorageClient, notice: Notice, image: NoticeImage) -> NoticeDTO:
    notice.images.remove(image)
    image.file.is_deleted = True

    await db.delete(image)
    await db.flush()

    return build_notice_dto(notice, None, storage)
