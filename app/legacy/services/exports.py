import asyncio
import io
import zipfile
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.legacy.models import AudioSegment, audio_capture_label_table
from app.legacy.services.labels import get_label_list
from app.s3 import S3StorageClient


async def export_audio_segments(
    *, db: AsyncSession, storage: S3StorageClient, audio_capture_label_option_ids: list[UUID] | None
) -> bytes:
    segments = []

    if audio_capture_label_option_ids != []:
        stmt = select(AudioSegment).where(AudioSegment.label_option_id.is_not(None))

        if audio_capture_label_option_ids is not None:
            stmt = stmt.where(
                select(audio_capture_label_table.c.label_option_id)
                .where(audio_capture_label_table.c.audio_capture_id == AudioSegment.audio_capture_id)
                .where(audio_capture_label_table.c.label_option_id.in_(audio_capture_label_option_ids))
                .exists()
            )

        segments = list(await db.scalars(stmt.order_by(AudioSegment.label_option_id, AudioSegment.created_at)))

    grouped = defaultdict(list)

    for segment in segments:
        grouped[segment.label_option_id].append(segment)

    categories = await get_label_list(db=db)

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for category in categories:
            for option in category.options:
                contents = await asyncio.gather(
                    *(storage.download(path=segment.audio_file.object_key) for segment in grouped[option.id])
                )

                for index, content in enumerate(contents, start=1):
                    await asyncio.to_thread(archive.writestr, f"{category.name}/{option.name}/{index:03d}.wav", content)

    return buffer.getvalue()
