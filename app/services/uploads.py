import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import sqs
from app.config import config
from app.db import session_factory, transactional
from app.enums import FileStatusEnum
from app.errors import InvalidProfilePhotoError
from app.models import Announcement, AnnouncementImage, File, Parrot, SessionSound, User
from app.s3 import s3
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
            content = await s3.download(path=key)

            try:
                photo = await prepare_uploaded_photo(content)
            except InvalidProfilePhotoError:
                logger.warning("이미지 검증 실패로 업로드를 거부함; key=%s", key)

                await s3.delete(path=key)
                await reject(db=db, file=file)

                return

            await s3.upload(path=path, file=photo)
            await s3.delete(path=key)

            size = len(photo)

        await confirm(db=db, file=file, path=path, size=size)

        if path.split("/")[2] == "session":
            stmt = select(SessionSound).where(SessionSound.audio_file_id == file.id)
            sound = await db.scalar(stmt)

            try:
                await sqs.send(
                    queue_url=config.SQS_PARROT_SOUND_DETECTION_QUEUE_URL,
                    body={
                        "type": "sound.detect_parrot",
                        "session_id": str(sound.session_id),
                        "data": [
                            {
                                "sound_id": str(sound.id),
                                "object_key": file.object_key,
                                "captured_at": sound.captured_at.isoformat(),
                            }
                        ],
                    },
                )
            except Exception:
                logger.exception("앵무새 소리 판별 요청 큐 전달 실패; sound_id=%s", sound.id)


@transactional
async def confirm(*, db: AsyncSession, file: File, path: str, size: int) -> None:
    parts = path.split("/")

    file.status = FileStatusEnum.UPLOADED.value
    file.file_size = size

    if parts[0] == "announcement":
        stmt = select(Announcement).where(Announcement.id == UUID(parts[1]))
        announcement = await db.scalar(stmt)

        if announcement is None:
            file.is_deleted = True

            return

        display_order = max((image.display_order for image in announcement.images), default=-1) + 1

        announcement.images.append(AnnouncementImage(file=file, display_order=display_order))

    elif parts[2] == "profile":
        stmt = select(User).where(User.id == UUID(parts[1]))
        user = await db.scalar(stmt)
        old_file = user.photo_file

        user.photo_file = file

        if user.uploading_photo_file_id == file.id:
            user.uploading_photo_file_id = None

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

        if parrot.uploading_photo_file_id == file.id:
            parrot.uploading_photo_file_id = None

        if old_file is not None:
            old_file.is_deleted = True


@transactional
async def reject(*, db: AsyncSession, file: File) -> None:
    file.status = FileStatusEnum.REJECTED.value
    file.is_deleted = True

    await db.flush()
