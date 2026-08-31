from uuid import UUID

from app.audio_capture.application.dto import GetAudioCaptureDetailDTO, GetAudioSegmentDTO
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo, IAudioSegmentRepo
from app.shared_kernel.domain.interfaces.services import IObjectStorageClient
from core.common.errors import ResourceNotFoundError


class GetAudioCaptureDetailUseCase:
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

    async def execute(self, *, audio_capture_id: UUID) -> GetAudioCaptureDetailDTO:
        capture = await self._audio_capture_repo.get_by_id(audio_capture_id=audio_capture_id)
        if capture is None:
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
