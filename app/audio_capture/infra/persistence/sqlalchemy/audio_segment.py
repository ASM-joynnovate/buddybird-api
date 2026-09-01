from uuid import UUID

from sqlalchemy import func, select, update

from app.audio_capture.domain.entities.audio_segment import AudioSegment
from app.audio_capture.domain.interfaces.repositories import IAudioSegmentRepo
from core.db import session, session_factory
from core.db.sqlalchemy.models import audio_capture_label_table


class AudioSegmentSQLAlchemyRepo(IAudioSegmentRepo):
    async def get_by_capture_id(self, *, audio_capture_id: UUID) -> list[AudioSegment]:
        async with session_factory() as read_session:
            stmt = (
                select(AudioSegment)
                .where(AudioSegment.audio_capture_id == audio_capture_id)
                .order_by(AudioSegment.start_ms)
            )

            result = await read_session.execute(stmt)

            return list(result.scalars().all())

    async def get_labeled(self, *, audio_capture_label_option_ids: list[UUID] | None) -> list[AudioSegment]:
        if audio_capture_label_option_ids is not None and not audio_capture_label_option_ids:
            return []

        async with session_factory() as read_session:
            stmt = select(AudioSegment).where(AudioSegment.label_option_id.is_not(None))

            if audio_capture_label_option_ids is not None:
                stmt = stmt.where(
                    select(audio_capture_label_table.c.label_option_id)
                    .where(audio_capture_label_table.c.audio_capture_id == AudioSegment.audio_capture_id)
                    .where(audio_capture_label_table.c.label_option_id.in_(audio_capture_label_option_ids))
                    .exists()
                )

            stmt = stmt.order_by(AudioSegment.label_option_id, AudioSegment.created_at)

            result = await read_session.execute(stmt)

            return list(result.scalars().all())

    async def get_counts_by_capture_ids(self, *, audio_capture_ids: list[UUID]) -> dict[UUID, tuple[int, int, int]]:
        if not audio_capture_ids:
            return {}

        async with session_factory() as read_session:
            stmt = (
                select(
                    AudioSegment.audio_capture_id,
                    func.count(AudioSegment.id),
                    func.count(AudioSegment.label_option_id),
                    func.count(AudioSegment.memo),
                )
                .where(AudioSegment.audio_capture_id.in_(audio_capture_ids))
                .group_by(AudioSegment.audio_capture_id)
            )

            result = await read_session.execute(stmt)

            return {row[0]: (row[1], row[2], row[3]) for row in result.all()}

    async def get_by_id(self, *, audio_segment_id: UUID) -> AudioSegment | None:
        stmt = select(AudioSegment).where(AudioSegment.id == audio_segment_id)

        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    async def detach_label_options(self, *, label_option_ids: list[UUID]) -> None:
        if not label_option_ids:
            return

        stmt = (
            update(AudioSegment).where(AudioSegment.label_option_id.in_(label_option_ids)).values(label_option_id=None)
        )

        await session.execute(stmt)

    async def save(self, *, audio_segment: AudioSegment) -> None:
        session.add(audio_segment)
