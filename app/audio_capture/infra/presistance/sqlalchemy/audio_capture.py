from uuid import UUID

from sqlalchemy import select

from app.audio_capture.domain.entities.audio_capture import AudioCapture
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo
from core.db import session, session_factory


class SQLAlchemyAudioCaptureRepo(IAudioCaptureRepo):
    async def get_by_id(self, *, audio_capture_id: UUID) -> AudioCapture | None:
        async with session_factory() as read_session:
            stmt = await read_session.execute(
                select(AudioCapture)
                .where(AudioCapture.id == audio_capture_id)
                .where(AudioCapture.is_deleted.is_(False))
            )

            return stmt.scalar_one_or_none()

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
