from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, tuple_

from app.audio_capture.domain.entities.audio_capture import AudioCapture
from app.audio_capture.domain.entities.audio_segment import AudioSegment
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo
from app.shared_kernel.domain.entities.file import File
from app.word.domain.entities.word import Word
from core.db import session, session_factory
from core.db.sqlalchemy.models import audio_capture_label_table


class AudioCaptureSQLAlchemyRepo(IAudioCaptureRepo):
    async def get_by_id(self, *, audio_capture_id: UUID) -> AudioCapture | None:
        stmt = select(AudioCapture).where(AudioCapture.id == audio_capture_id)

        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_list(
        self,
        *,
        user_id: str | None,
        word_label: str | None,
        label_option_ids: list[UUID] | None,
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
        prev: int,
        limit: int,
    ) -> list[AudioCapture]:
        if label_option_ids is not None and not label_option_ids:
            return []

        memo_exists = (
            select(AudioSegment.id)
            .where(AudioSegment.audio_capture_id == AudioCapture.id)
            .where(AudioSegment.memo.is_not(None))
            .exists()
        )

        async with session_factory() as read_session:
            stmt = select(AudioCapture)

            if user_id is not None:
                stmt = stmt.where(AudioCapture.firebase_anon_uid == user_id)

            if date_from is not None:
                stmt = stmt.where(AudioCapture.captured_at >= date_from)
            if date_to is not None:
                stmt = stmt.where(AudioCapture.captured_at <= date_to)

            if word_label is not None:
                stmt = stmt.join(Word, AudioCapture.word_id == Word.id).where(Word.label == word_label)

            if label_option_ids is not None:
                label_filter = (
                    select(audio_capture_label_table.c.label_option_id)
                    .where(audio_capture_label_table.c.audio_capture_id == AudioCapture.id)
                    .where(audio_capture_label_table.c.label_option_id.in_(label_option_ids))
                    .exists()
                )
                stmt = stmt.where(label_filter)

            if has_memo is not None:
                stmt = stmt.where(memo_exists if has_memo else ~memo_exists)

            stmt = stmt.order_by(AudioCapture.created_at.desc()).offset(prev).limit(limit)

            result = await read_session.execute(stmt)

            return list(result.scalars().all())

    async def get_count(
        self,
        *,
        user_id: str | None,
        word_label: str | None,
        label_option_ids: list[UUID] | None,
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        if label_option_ids is not None and not label_option_ids:
            return 0

        memo_exists = (
            select(AudioSegment.id)
            .where(AudioSegment.audio_capture_id == AudioCapture.id)
            .where(AudioSegment.memo.is_not(None))
            .exists()
        )

        async with session_factory() as read_session:
            stmt = select(func.count()).select_from(AudioCapture)

            if user_id is not None:
                stmt = stmt.where(AudioCapture.firebase_anon_uid == user_id)

            if date_from is not None:
                stmt = stmt.where(AudioCapture.captured_at >= date_from)
            if date_to is not None:
                stmt = stmt.where(AudioCapture.captured_at <= date_to)

            if word_label is not None:
                stmt = stmt.join(Word, AudioCapture.word_id == Word.id).where(Word.label == word_label)

            if label_option_ids is not None:
                label_filter = (
                    select(audio_capture_label_table.c.label_option_id)
                    .where(audio_capture_label_table.c.audio_capture_id == AudioCapture.id)
                    .where(audio_capture_label_table.c.label_option_id.in_(label_option_ids))
                    .exists()
                )
                stmt = stmt.where(label_filter)

            if has_memo is not None:
                stmt = stmt.where(memo_exists if has_memo else ~memo_exists)

            result = await read_session.execute(stmt)

            return result.scalar_one()

    async def get_existing_client_capture_ids(self, *, user_id: str, client_capture_ids: list[str]) -> set[str]:
        if not client_capture_ids:
            return set()

        async with session_factory() as read_session:
            stmt = (
                select(AudioCapture.client_capture_id)
                .where(AudioCapture.firebase_anon_uid == user_id)
                .where(AudioCapture.client_capture_id.in_(client_capture_ids))
            )

            result = await read_session.execute(stmt)

            return set(result.scalars().all())

    async def detach_label_options(self, *, label_option_ids: list[UUID]) -> None:
        if not label_option_ids:
            return

        stmt = delete(audio_capture_label_table).where(
            audio_capture_label_table.c.label_option_id.in_(label_option_ids)
        )

        await session.execute(stmt)

    async def get_by_audio_file_path(self, *, file_path: str, file_name: str) -> AudioCapture | None:
        stmt = (
            select(AudioCapture)
            .join(File, AudioCapture.audio_file_id == File.id)
            .where(File.file_path == file_path)
            .where(File.file_name == file_name)
        )

        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_by_audio_file_paths(self, *, audio_file_paths: list[tuple[str, str]]) -> list[AudioCapture]:
        if not audio_file_paths:
            return []

        stmt = (
            select(AudioCapture)
            .join(File, AudioCapture.audio_file_id == File.id)
            .where(tuple_(File.file_path, File.file_name).in_(audio_file_paths))
        )

        result = await session.execute(stmt)

        return list(result.scalars().all())

    async def save(self, *, audio_capture: AudioCapture) -> None:
        session.add(audio_capture)
