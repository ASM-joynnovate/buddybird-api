from datetime import datetime
from uuid import UUID

from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo


class GetAudioCaptureCountUseCase:
    def __init__(
        self,
        *,
        audio_capture_repo: IAudioCaptureRepo,
    ):
        self._audio_capture_repo = audio_capture_repo

    async def execute(
        self,
        *,
        firebase_anon_uid: str | None,
        word_label: str | None,
        label_option_ids: list[UUID] | None,
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        return await self._audio_capture_repo.get_count(
            user_id=firebase_anon_uid,
            word_label=word_label,
            label_option_ids=label_option_ids,
            has_memo=has_memo,
            date_from=date_from,
            date_to=date_to,
        )
