import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import session_factory, transactional
from app.enums import FileStatusEnum
from app.errors import InvalidProfilePhotoError
from app.models import File, Notice, NoticeImage, Parrot, User
from app.s3 import get_s3
from app.services.users import prepare_uploaded_photo

logger = logging.getLogger(__name__)


async def process(*, key: str, size: int) -> None:
    path = key.removeprefix("upload/")

    async with session_factory() as db:
        stmt = select(File).where(File.id == UUID(path.split("/")[-2]))
        file = await db.scalar(stmt)

        if file is None or file.status != FileStatusEnum.PENDING.value:
            logger.info("확정할 업로드가 없어 건너뜀; key=%s", key)

            return

        if key != path:
            storage = get_s3()
            content = await storage.download(path=key)

            try:
                photo = await prepare_uploaded_photo(content)
            except InvalidProfilePhotoError:
                logger.warning("이미지 검증 실패로 업로드를 거부함; key=%s", key)

                await storage.delete(path=key)
                await reject(db=db, file=file)

                return

            await storage.upload(path=path, file=photo)
            await storage.delete(path=key)

            size = len(photo)

        await confirm(db=db, file=file, path=path, size=size)


@transactional
async def confirm(*, db: AsyncSession, file: File, path: str, size: int) -> None:
    parts = path.split("/")

    file.status = FileStatusEnum.UPLOADED.value
    file.file_size = size

    if parts[0] == "notice":
        stmt = select(Notice).where(Notice.id == UUID(parts[1]))
        notice = await db.scalar(stmt)

        if notice is None:
            file.is_deleted = True

            return

        display_order = max((image.display_order for image in notice.images), default=-1) + 1

        notice.images.append(NoticeImage(file=file, display_order=display_order))

    elif parts[2] == "profile":
        stmt = select(User).where(User.id == UUID(parts[1]))
        user = await db.scalar(stmt)
        old_file = user.photo_file

        user.photo_file = file

        if old_file is not None:
            old_file.is_deleted = True

    elif parts[2] == "parrot":
        stmt = select(Parrot).where(Parrot.id == UUID(parts[3]))
        parrot = await db.scalar(stmt)

        if parrot is None:
            file.is_deleted = True

            return

        old_file = parrot.photo_file

        parrot.photo_file = file

        if old_file is not None:
            old_file.is_deleted = True


@transactional
async def reject(*, db: AsyncSession, file: File) -> None:
    file.status = FileStatusEnum.REJECTED.value
    file.is_deleted = True

    await db.flush()
