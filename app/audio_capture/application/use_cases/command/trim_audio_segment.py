from functools import partial
from uuid import UUID

from app.audio_capture.application.dto import TrimAudioSegmentDTO
from app.audio_capture.domain.commands import TrimAudioSegmentCommand
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo, IAudioSegmentRepo
from app.audio_capture.domain.interfaces.services import IAudioAnalyzer
from app.audio_capture.domain.value_objects import AudioSegmentRange
from app.shared_kernel.domain.commands import AssignFileCommand
from app.shared_kernel.domain.interfaces.services import IObjectStorageClient
from core.common.errors import ResourceNotFoundError
from core.db import Transactional, on_rollback


class TrimAudioSegmentUseCase:
    def __init__(
        self,
        *,
        object_storage_client: IObjectStorageClient,
        audio_analyzer: IAudioAnalyzer,
        audio_capture_repo: IAudioCaptureRepo,
        audio_segment_repo: IAudioSegmentRepo,
    ):
        self._object_storage_client = object_storage_client
        self._audio_analyzer = audio_analyzer
        self._audio_capture_repo = audio_capture_repo
        self._audio_segment_repo = audio_segment_repo

    @Transactional()
    async def execute(self, *, audio_segment_id: UUID, data: TrimAudioSegmentDTO) -> None:
        segment = await self._audio_segment_repo.get_by_id(audio_segment_id=audio_segment_id)
        if segment is None:
            raise ResourceNotFoundError

        capture = await self._audio_capture_repo.get_by_id(audio_capture_id=segment.audio_capture_id)
        if capture is None:
            raise ResourceNotFoundError

        segment_range = AudioSegmentRange(start_ms=data.start_ms, end_ms=data.end_ms)
        source_path = f"{capture.audio_file.file_path}/{capture.audio_file.file_name}"
        source = await self._object_storage_client.download(path=source_path)
        trimmed = self._audio_analyzer.trim(file=source, start_ms=segment_range.start_ms, end_ms=segment_range.end_ms)

        segment.retrim(
            command=TrimAudioSegmentCommand(
                range=segment_range,
                audio_file=AssignFileCommand(name=segment.audio_file.file_name, type="audio/wav", file=trimmed),
            )
        )

        segment_path = f"{segment.audio_file.file_path}/{segment.audio_file.file_name}"
        on_rollback(partial(self._object_storage_client.delete, path=segment_path))

        await self._object_storage_client.upload(path=segment_path, file=trimmed)
