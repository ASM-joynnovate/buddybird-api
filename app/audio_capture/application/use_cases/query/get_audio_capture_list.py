from datetime import datetime
from uuid import UUID

from app.audio_capture.application.dto import GetAudioCaptureListItemDTO
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo, IAudioSegmentRepo


class GetAudioCaptureListUseCase:
    def __init__(
        self,
        *,
        audio_capture_repo: IAudioCaptureRepo,
        audio_segment_repo: IAudioSegmentRepo,
    ):
        self._audio_capture_repo = audio_capture_repo
        self._audio_segment_repo = audio_segment_repo

    async def execute(
        self,
        *,
        firebase_anon_uid: str | None,
        word_label: str | None,
        label_option_ids: list[UUID] | None,
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
        prev: int,
        limit: int,
    ) -> list[GetAudioCaptureListItemDTO]:
        captures = await self._audio_capture_repo.get_list(
            user_id=firebase_anon_uid,
            word_label=word_label,
            label_option_ids=label_option_ids,
            has_memo=has_memo,
            date_from=date_from,
            date_to=date_to,
            prev=prev,
            limit=limit,
        )
        counts = await self._audio_segment_repo.get_counts_by_capture_ids(
            audio_capture_ids=[capture.id for capture in captures]
        )

        return [
            GetAudioCaptureListItemDTO(
                id=capture.id,
                firebase_anon_uid=capture.firebase_anon_uid,
                client_word_id=capture.client_word_id,
                word_id=capture.word_id,
                cycle=capture.cycle,
                phase=capture.phase,
                captured_at=capture.captured_at,
                duration_ms=capture.duration_ms,
                created_at=capture.created_at,
                segment_count=counts.get(capture.id, (0, 0, 0))[0],
                labeled_count=counts.get(capture.id, (0, 0, 0))[1],
                has_memo=counts.get(capture.id, (0, 0, 0))[2] > 0,
                label_option_ids=[option.id for option in capture.label_options],
            )
            for capture in captures
        ]
