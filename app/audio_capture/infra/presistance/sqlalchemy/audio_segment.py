from uuid import UUID

from sqlalchemy import func, select

from app.audio_capture.domain.entities.audio_segment import AudioSegment
from app.audio_capture.domain.interfaces.repositories.audio_segment import IAudioSegmentRepo
from core.db import session, session_factory


class SQLAlchemyAudioSegmentRepo(IAudioSegmentRepo):
    async def get_by_capture_id(self, *, audio_capture_id: UUID) -> list[AudioSegment]:
        async with session_factory() as read_session:
            result = await read_session.execute(
                select(AudioSegment)
                .where(AudioSegment.audio_capture_id == audio_capture_id)
                .where(AudioSegment.is_deleted.is_(False))
                .order_by(AudioSegment.start_ms)
            )
            return result.scalars().all()

    async def get_labeled(self, *, audio_capture_label_option_ids: list[UUID] | None = None) -> list[AudioSegment]:
        from core.db.sqlalchemy.models import audio_capture_label_table

        async with session_factory() as read_session:
            stmt = (
                select(AudioSegment)
                .where(AudioSegment.label_option_id.is_not(None))
                .where(AudioSegment.is_deleted.is_(False))
            )

            if audio_capture_label_option_ids:
                stmt = stmt.where(
                    select(audio_capture_label_table.c.label_option_id)
                    .where(audio_capture_label_table.c.audio_capture_id == AudioSegment.audio_capture_id)
                    .where(audio_capture_label_table.c.label_option_id.in_(audio_capture_label_option_ids))
                    .exists()
                )

            stmt = stmt.order_by(AudioSegment.label_option_id, AudioSegment.created_at)

            result = await read_session.execute(stmt)
            return result.scalars().all()

    async def get_counts_by_capture_ids(self, *, audio_capture_ids: list[UUID]) -> dict[UUID, tuple[int, int, int]]:
        if not audio_capture_ids:
            return {}

        async with session_factory() as read_session:
            result = await read_session.execute(
                select(
                    AudioSegment.audio_capture_id,
                    func.count(AudioSegment.id),
                    func.count(AudioSegment.label_option_id),
                    func.count(AudioSegment.memo),
                )
                .where(AudioSegment.audio_capture_id.in_(audio_capture_ids))
                .where(AudioSegment.is_deleted.is_(False))
                .group_by(AudioSegment.audio_capture_id)
            )
            return {row[0]: (row[1], row[2], row[3]) for row in result.all()}

    async def get_by_id(self, *, audio_segment_id: UUID) -> AudioSegment | None:
        result = await session.execute(
            select(AudioSegment).where(AudioSegment.id == audio_segment_id).where(AudioSegment.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()

    async def save(self, *, audio_segment: AudioSegment) -> None:
        session.add(audio_segment)
