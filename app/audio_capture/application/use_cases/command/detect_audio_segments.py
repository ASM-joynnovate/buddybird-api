import asyncio
from functools import partial
from uuid import UUID

from app.audio_capture.domain.commands import CreateAudioSegmentCommand
from app.audio_capture.domain.entities.audio_segment import AudioSegment
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo, IAudioSegmentRepo
from app.audio_capture.domain.interfaces.services import IAudioAnalyzer, IVadService
from app.audio_capture.domain.value_objects import AudioSegmentRange
from app.shared_kernel.domain.commands import AssignFileCommand
from app.shared_kernel.domain.interfaces.services import IObjectStorageClient
from core.common.errors import ResourceNotFoundError
from core.db import Transactional, on_rollback


class DetectAudioSegmentsUseCase:
    def __init__(
        self,
        *,
        object_storage_client: IObjectStorageClient,
        audio_analyzer: IAudioAnalyzer,
        vad_service: IVadService,
        audio_capture_repo: IAudioCaptureRepo,
        audio_segment_repo: IAudioSegmentRepo,
    ):
        self._object_storage_client = object_storage_client
        self._audio_analyzer = audio_analyzer
        self._vad_service = vad_service
        self._audio_capture_repo = audio_capture_repo
        self._audio_segment_repo = audio_segment_repo

    @Transactional()
    async def execute(self, *, audio_capture_id: UUID) -> None:
        capture = await self._audio_capture_repo.get_by_id(audio_capture_id=audio_capture_id)
        if capture is None:
            raise ResourceNotFoundError

        source = await self._object_storage_client.download(
            path=f"{capture.audio_file.file_path}/{capture.audio_file.file_name}"
        )
        ranges = await asyncio.to_thread(self._vad_service.detect, file=source)

        async with asyncio.TaskGroup() as task_group:
            for start_ms, end_ms in ranges:
                trimmed = self._audio_analyzer.trim(file=source, start_ms=start_ms, end_ms=end_ms)
                segment = AudioSegment.create(
                    command=CreateAudioSegmentCommand(
                        audio_capture_id=capture.id,
                        firebase_anon_uid=capture.firebase_anon_uid,
                        range=AudioSegmentRange(start_ms=start_ms, end_ms=end_ms),
                        audio_file=AssignFileCommand(name=capture.audio_file.file_name, type="audio/wav", file=trimmed),
                    )
                )
                await self._audio_segment_repo.save(audio_segment=segment)

                segment_path = f"{segment.audio_file.file_path}/{segment.audio_file.file_name}"
                on_rollback(partial(self._object_storage_client.delete, path=segment_path))

                task_group.create_task(self._object_storage_client.upload(path=segment_path, file=trimmed))
