import io
import logging
import wave
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import queues
from app.db import session_factory, transactional
from app.enums import FileStatusEnum
from app.errors import InvalidAdImageError, InvalidProfilePhotoError
from app.file import confirm_uploaded_photo
from app.models import File, Parrot, SessionSound, User
from app.r2 import r2
from app.services import notifications

logger = logging.getLogger(__name__)


async def process(*, key: str, size: int) -> None:
    path = key.removeprefix("upload/")

    async with session_factory() as db:
        stmt = select(File).where(File.id == UUID(path.split("/")[-2]))
        file = await db.scalar(stmt)

        if file is not None and file.status == FileStatusEnum.UPLOADED.value and path.split("/")[2] == "petcam":
            delivery_ids = await notifications.create_emergency_notification(db=db, image_file_id=file.id)

            await notifications.enqueue_push_deliveries(*delivery_ids)

            return

        if file is None or file.status != FileStatusEnum.PENDING.value:
            logger.info("확정할 업로드가 없어 건너뜀; key=%s", key)

            return

        if key != path:
            try:
                await confirm_uploaded_photo(storage=r2, file=file)
            except InvalidAdImageError, InvalidProfilePhotoError:
                logger.warning("이미지 검증 실패로 업로드를 거부함; key=%s", key)

                await r2.delete(path=key)
                await reject(db=db, file=file)

                return

            size = file.file_size

        duration_ms = None

        if path.split("/")[2] == "session":
            content = await r2.download(path=key)

            try:
                with wave.open(io.BytesIO(content)) as audio:
                    duration_ms = audio.getnframes() * 1000 // audio.getframerate()
            except wave.Error, EOFError, ZeroDivisionError:
                logger.warning("WAV 길이 계산 실패; key=%s", key)

        await confirm(db=db, file=file, path=path, size=size, duration_ms=duration_ms)

        if path.split("/")[2] == "session":
            stmt = select(SessionSound).where(SessionSound.audio_file_id == file.id)
            sound = await db.scalar(stmt)

            try:
                await queues.send(
                    queue="parrot-sound-detection",
                    body={
                        "type": "audio.detect_parrot",
                        "session_id": str(sound.session_id),
                        "data": [
                            {
                                "audio_id": str(sound.id),
                                "object_key": file.object_key,
                                "captured_at": sound.captured_at.isoformat(),
                            }
                        ],
                    },
                )
            except Exception:
                logger.exception("앵무새 소리 판별 요청 큐 전달 실패; sound_id=%s", sound.id)

        if path.split("/")[2] == "petcam":
            delivery_ids = await notifications.create_emergency_notification(db=db, image_file_id=file.id)

            await notifications.enqueue_push_deliveries(*delivery_ids)


@transactional
async def confirm(*, db: AsyncSession, file: File, path: str, size: int, duration_ms: int | None) -> None:
    parts = path.split("/")

    file.status = FileStatusEnum.UPLOADED.value
    file.file_size = size

    if parts[2] == "profile":
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

    elif parts[2] == "session":
        stmt = select(SessionSound).where(SessionSound.audio_file_id == file.id)
        sound = await db.scalar(stmt)

        sound.duration_ms = duration_ms


@transactional
async def reject(*, db: AsyncSession, file: File) -> None:
    file.status = FileStatusEnum.REJECTED.value
    file.is_deleted = True

    await db.flush()
