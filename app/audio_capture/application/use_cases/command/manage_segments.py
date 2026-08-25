import asyncio
from functools import partial
from uuid import UUID

from app.audio_capture.application.dto.audio_segment import (
    AssignAudioSegmentLabelDTO,
    CreateAudioSegmentDTO,
    TrimAudioSegmentDTO,
    UpdateAudioSegmentMemoDTO,
)
from app.audio_capture.domain.command.audio_segment import (
    AssignAudioSegmentLabelCommand,
    CreateAudioSegmentCommand,
    TrimAudioSegmentCommand,
    UpdateAudioSegmentMemoCommand,
)
from app.audio_capture.domain.entities.audio_segment import AudioSegment
from app.audio_capture.domain.interfaces.repositories import (
    IAudioCaptureRepo,
    IAudioSegmentRepo,
    ILabelOptionRepo,
)
from app.audio_capture.domain.interfaces.services import IAudioAnalyzer, IVadService
from app.audio_capture.domain.value_objects import AudioSegmentRange
from app.shared_kernel.domain.command.file import AssignFileCommand
from app.shared_kernel.domain.interfaces.object_storage import IObjectStorageClient
from core.common.errors import ResourceNotFoundError
from core.db import Transactional
from core.db.transactional import on_rollback


class CreateAudioSegmentUseCase:
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
    async def execute(self, *, audio_capture_id: UUID, data: CreateAudioSegmentDTO) -> None:
        capture = await self._audio_capture_repo.get_by_id(audio_capture_id=audio_capture_id)
        if capture is None:
            raise ResourceNotFoundError

        segment_range = AudioSegmentRange(start_ms=data.start_ms, end_ms=data.end_ms)
        source = await self._object_storage_client.download(
            path=f"{capture.audio_file.file_path}/{capture.audio_file.file_name}"
        )
        trimmed = self._audio_analyzer.trim(file=source, start_ms=segment_range.start_ms, end_ms=segment_range.end_ms)

        segment = AudioSegment.create(
            command=CreateAudioSegmentCommand(
                audio_capture_id=capture.id,
                firebase_anon_uid=capture.firebase_anon_uid,
                range=segment_range,
                audio_file=AssignFileCommand(name=capture.audio_file.file_name, type="audio/wav", file=trimmed),
            )
        )
        await self._audio_segment_repo.save(audio_segment=segment)

        segment_path = f"{segment.audio_file.file_path}/{segment.audio_file.file_name}"
        on_rollback(partial(self._object_storage_client.delete, path=segment_path))
        await self._object_storage_client.upload(path=segment_path, file=trimmed)


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


class DeleteAudioSegmentUseCase:
    def __init__(self, *, audio_segment_repo: IAudioSegmentRepo):
        self._audio_segment_repo = audio_segment_repo

    @Transactional()
    async def execute(self, *, audio_segment_id: UUID) -> None:
        segment = await self._audio_segment_repo.get_by_id(audio_segment_id=audio_segment_id)
        if segment is None:
            raise ResourceNotFoundError

        segment.delete()


class AssignAudioSegmentLabelUseCase:
    def __init__(self, *, audio_segment_repo: IAudioSegmentRepo, label_option_repo: ILabelOptionRepo):
        self._audio_segment_repo = audio_segment_repo
        self._label_option_repo = label_option_repo

    @Transactional()
    async def execute(self, *, audio_segment_id: UUID, data: AssignAudioSegmentLabelDTO) -> None:
        segment = await self._audio_segment_repo.get_by_id(audio_segment_id=audio_segment_id)
        if segment is None:
            raise ResourceNotFoundError

        option = await self._label_option_repo.get_by_id(label_option_id=data.label_option_id)
        if option is None:
            raise ResourceNotFoundError

        segment.assign_label(command=AssignAudioSegmentLabelCommand(label_option_id=data.label_option_id))


class UpdateAudioSegmentMemoUseCase:
    def __init__(self, *, audio_segment_repo: IAudioSegmentRepo):
        self._audio_segment_repo = audio_segment_repo

    @Transactional()
    async def execute(self, *, audio_segment_id: UUID, data: UpdateAudioSegmentMemoDTO) -> None:
        segment = await self._audio_segment_repo.get_by_id(audio_segment_id=audio_segment_id)
        if segment is None:
            raise ResourceNotFoundError

        segment.update_memo(command=UpdateAudioSegmentMemoCommand(memo=data.memo))


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
