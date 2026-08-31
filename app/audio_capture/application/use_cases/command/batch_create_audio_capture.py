import io
import zipfile
from functools import partial

from app.audio_capture.application.dto import (
    BatchCreateAudioCaptureDTO,
    BatchCreateAudioCaptureResultDTO,
    CreateAudioCaptureItemDTO,
)
from app.audio_capture.application.errors import (
    AudioCaptureArchiveEntryNotFoundError,
    AudioCaptureArchiveInvalidError,
)
from app.audio_capture.domain.commands import CreateAudioCaptureCommand
from app.audio_capture.domain.entities.audio_capture import AudioCapture
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo
from app.audio_capture.domain.interfaces.services import IAudioAnalyzer
from app.shared_kernel.domain.commands import AssignFileCommand
from app.shared_kernel.domain.interfaces.services import IFileAnalyzer, IObjectStorageClient
from core.common.errors import CustomError
from core.db import Transactional, on_rollback


class BatchCreateAudioCaptureUseCase:
    def __init__(
        self,
        *,
        object_storage_client: IObjectStorageClient,
        file_analyzer: IFileAnalyzer,
        audio_analyzer: IAudioAnalyzer,
        audio_capture_repo: IAudioCaptureRepo,
    ):
        self._object_storage_client = object_storage_client
        self._file_analyzer = file_analyzer
        self._audio_analyzer = audio_analyzer
        self._audio_capture_repo = audio_capture_repo

    @Transactional()
    async def execute(self, *, data: BatchCreateAudioCaptureDTO) -> dict[str, BatchCreateAudioCaptureResultDTO]:
        try:
            archive = zipfile.ZipFile(io.BytesIO(data.archive_file))
        except zipfile.BadZipFile as e:
            raise AudioCaptureArchiveInvalidError from e

        # 이미 저장된(firebase_anon_id, client_capture_id 조합이 동일한) 데이터 불러오기
        saved_client_capture_ids = await self._audio_capture_repo.get_existing_client_capture_ids(
            user_id=data.firebase_anon_uid,
            client_capture_ids=[item.client_capture_id for item in data.items],
        )

        results: dict[str, BatchCreateAudioCaptureResultDTO] = {}
        with archive:
            for item in data.items:
                # 저장되어있으면 다시 저장하지 않고 패스
                if item.client_capture_id in saved_client_capture_ids:
                    results[item.client_capture_id] = BatchCreateAudioCaptureResultDTO(status="success")
                    continue

                try:
                    await self._save_one(data=data, item=item, archive=archive)
                except CustomError as e:
                    results[item.client_capture_id] = BatchCreateAudioCaptureResultDTO(
                        status="rejected",
                        code=e.code,
                        error_code=e.error_code,
                        message=e.message,
                    )
                    continue

                saved_client_capture_ids.add(item.client_capture_id)
                results[item.client_capture_id] = BatchCreateAudioCaptureResultDTO(status="success")

        return results

    async def _save_one(
        self,
        *,
        data: BatchCreateAudioCaptureDTO,
        item: CreateAudioCaptureItemDTO,
        archive: zipfile.ZipFile,
    ) -> None:
        try:
            audio = archive.read(item.file_name)
        except KeyError as e:
            raise AudioCaptureArchiveEntryNotFoundError from e
        except zipfile.BadZipFile as e:
            raise AudioCaptureArchiveInvalidError from e

        file_type = self._file_analyzer.get_mime_type(file=audio)
        duration_ms = self._audio_analyzer.get_duration_ms(file=audio)

        audio_capture = AudioCapture.create(
            command=CreateAudioCaptureCommand(
                client_capture_id=item.client_capture_id,
                client_session_id=item.client_session_id,
                firebase_anon_uid=data.firebase_anon_uid,
                word_id=None,
                client_word_id=item.client_word_id,
                cycle=item.cycle,
                phase=item.phase,
                captured_at=item.captured_at,
                duration_ms=duration_ms,
                audio_file=AssignFileCommand(name=item.file_name, type=file_type, file=audio),
                parrot_species=item.parrot_species,
                parrot_birthdate=item.parrot_birthdate,
                app_version=item.app_version,
                device_platform=data.device_platform,
                device_os_version=data.device_os_version,
                device_model=data.device_model,
            )
        )
        await self._audio_capture_repo.save(audio_capture=audio_capture)

        audio_file_path = f"{audio_capture.audio_file.file_path}/{audio_capture.audio_file.file_name}"
        on_rollback(partial(self._object_storage_client.delete, path=audio_file_path))
        await self._object_storage_client.upload(path=audio_file_path, file=audio)
