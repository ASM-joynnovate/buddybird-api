from datetime import datetime
from uuid import UUID

from app.audio_capture.application.dto.audio_capture import (
    GetAudioCaptureDetailDTO,
    GetAudioCaptureListItemDTO,
)
from app.audio_capture.application.dto.audio_segment import GetAudioSegmentDTO
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo, IAudioSegmentRepo
from app.shared_kernel.domain.interfaces.object_storage import IObjectStorageClient
from core.common.errors import ResourceNotFoundError


class AudioCaptureQueryUseCase:
    def __init__(
        self,
        *,
        audio_capture_repo: IAudioCaptureRepo,
        audio_segment_repo: IAudioSegmentRepo,
        object_storage_client: IObjectStorageClient,
    ):
        self._audio_capture_repo = audio_capture_repo
        self._audio_segment_repo = audio_segment_repo
        self._object_storage_client = object_storage_client

    async def get_list(
        self,
        *,
        firebase_anon_uid: str | None,
        word_label: str | None,
        label_option_ids: list[UUID],
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
        prev: int,
        limit: int,
    ) -> list[GetAudioCaptureListItemDTO]:
        captures = await self._audio_capture_repo.get_list(
            firebase_anon_uid=firebase_anon_uid,
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

    async def get_count(
        self,
        *,
        firebase_anon_uid: str | None,
        word_label: str | None,
        label_option_ids: list[UUID],
        has_memo: bool | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> int:
        return await self._audio_capture_repo.get_count(
            firebase_anon_uid=firebase_anon_uid,
            word_label=word_label,
            label_option_ids=label_option_ids,
            has_memo=has_memo,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_detail(self, *, audio_capture_id: UUID) -> GetAudioCaptureDetailDTO:
        capture = await self._audio_capture_repo.get_by_id(audio_capture_id=audio_capture_id)
        if not capture:
            raise ResourceNotFoundError

        segments = await self._audio_segment_repo.get_by_capture_id(audio_capture_id=capture.id)

        audio_url = await self._object_storage_client.generate_presigned_url(
            path=f"{capture.audio_file.file_path}/{capture.audio_file.file_name}"
        )

        segment_dtos = []
        for segment in segments:
            segment_url = await self._object_storage_client.generate_presigned_url(
                path=f"{segment.audio_file.file_path}/{segment.audio_file.file_name}"
            )
            segment_dtos.append(
                GetAudioSegmentDTO(
                    id=segment.id,
                    start_ms=segment.range.start_ms,
                    end_ms=segment.range.end_ms,
                    label_option_id=segment.label_option_id,
                    memo=segment.memo,
                    audio_url=segment_url,
                )
            )

        return GetAudioCaptureDetailDTO(
            id=capture.id,
            firebase_anon_uid=capture.firebase_anon_uid,
            client_word_id=capture.client_word_id,
            word_id=capture.word_id,
            cycle=capture.cycle,
            phase=capture.phase,
            captured_at=capture.captured_at,
            duration_ms=capture.duration_ms,
            parrot_species=capture.parrot_species,
            parrot_birthdate=capture.parrot_birthdate,
            created_at=capture.created_at,
            audio_url=audio_url,
            segments=segment_dtos,
            label_option_ids=[option.id for option in capture.label_options],
        )
