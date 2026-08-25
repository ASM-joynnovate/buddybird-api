from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from app.audio_capture.domain.entities.audio_capture import AudioCapture
from app.audio_capture.domain.enum import LabelStatusEnum
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo
from core.db import session, session_factory
from core.db.sqlalchemy.models import audio_segment_table, word_table


class SQLAlchemyAudioCaptureRepo(IAudioCaptureRepo):
    async def get_by_id(self, *, audio_capture_id: UUID) -> AudioCapture | None:
        async with session_factory() as read_session:
            stmt = await read_session.execute(
                select(AudioCapture)
                .where(AudioCapture.id == audio_capture_id)
                .where(AudioCapture.is_deleted.is_(False))
            )

            return stmt.scalar_one_or_none()

    async def get_list(
        self,
        *,
        firebase_anon_uid: str | None,
        word_label: str | None,
        label_status: LabelStatusEnum,
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
        prev: int,
        limit: int,
    ) -> list[AudioCapture]:
        labeled_exists = (
            select(audio_segment_table.c.id)
            .where(audio_segment_table.c.audio_capture_id == AudioCapture.id)
            .where(audio_segment_table.c.label_option_id.is_not(None))
            .where(audio_segment_table.c.is_deleted.is_(False))
            .exists()
        )
        memo_exists = (
            select(audio_segment_table.c.id)
            .where(audio_segment_table.c.audio_capture_id == AudioCapture.id)
            .where(audio_segment_table.c.memo.is_not(None))
            .where(audio_segment_table.c.is_deleted.is_(False))
            .exists()
        )

        async with session_factory() as read_session:
            stmt = select(AudioCapture).where(AudioCapture.is_deleted.is_(False))

            if firebase_anon_uid is not None:
                stmt = stmt.where(AudioCapture.firebase_anon_uid == firebase_anon_uid)

            if date_from is not None:
                stmt = stmt.where(AudioCapture.captured_at >= date_from)
            if date_to is not None:
                stmt = stmt.where(AudioCapture.captured_at <= date_to)

            if word_label is not None:
                stmt = stmt.join(word_table, AudioCapture.word_id == word_table.c.id).where(
                    word_table.c.label == word_label
                )

            if label_status == LabelStatusEnum.LABELED:
                stmt = stmt.where(labeled_exists)
            elif label_status == LabelStatusEnum.UNLABELED:
                stmt = stmt.where(~labeled_exists)

            if has_memo:
                stmt = stmt.where(memo_exists)
            elif has_memo is False:
                stmt = stmt.where(~memo_exists)

            stmt = stmt.order_by(AudioCapture.created_at.desc()).offset(prev).limit(limit)

            result = await read_session.execute(stmt)
            return result.scalars().all()

    async def get_count(
        self,
        *,
        firebase_anon_uid: str | None,
        word_label: str | None,
        label_status: LabelStatusEnum,
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        labeled_exists = (
            select(audio_segment_table.c.id)
            .where(audio_segment_table.c.audio_capture_id == AudioCapture.id)
            .where(audio_segment_table.c.label_option_id.is_not(None))
            .where(audio_segment_table.c.is_deleted.is_(False))
            .exists()
        )
        memo_exists = (
            select(audio_segment_table.c.id)
            .where(audio_segment_table.c.audio_capture_id == AudioCapture.id)
            .where(audio_segment_table.c.memo.is_not(None))
            .where(audio_segment_table.c.is_deleted.is_(False))
            .exists()
        )

        async with session_factory() as read_session:
            stmt = select(func.count()).select_from(AudioCapture).where(AudioCapture.is_deleted.is_(False))

            if firebase_anon_uid is not None:
                stmt = stmt.where(AudioCapture.firebase_anon_uid == firebase_anon_uid)

            if date_from is not None:
                stmt = stmt.where(AudioCapture.captured_at >= date_from)
            if date_to is not None:
                stmt = stmt.where(AudioCapture.captured_at <= date_to)

            if word_label is not None:
                stmt = stmt.join(word_table, AudioCapture.word_id == word_table.c.id).where(
                    word_table.c.label == word_label
                )

            if label_status == LabelStatusEnum.LABELED:
                stmt = stmt.where(labeled_exists)
            elif label_status == LabelStatusEnum.UNLABELED:
                stmt = stmt.where(~labeled_exists)

            if has_memo:
                stmt = stmt.where(memo_exists)
            elif has_memo is False:
                stmt = stmt.where(~memo_exists)

            result = await read_session.execute(stmt)
            return result.scalar_one()

    async def get_existing_client_capture_ids(
        self, *, firebase_anon_uid: str, client_capture_ids: list[str]
    ) -> set[str]:
        if not client_capture_ids:
            return set()

        async with session_factory() as read_session:
            result = await read_session.execute(
                select(AudioCapture.client_capture_id)
                .where(AudioCapture.firebase_anon_uid == firebase_anon_uid)
                .where(AudioCapture.client_capture_id.in_(client_capture_ids))
            )

            return set(result.scalars().all())

    async def save(self, *, audio_capture: AudioCapture) -> None:
        session.add(audio_capture)
