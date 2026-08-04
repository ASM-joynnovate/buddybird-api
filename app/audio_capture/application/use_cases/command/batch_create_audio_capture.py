import io
import zipfile
from functools import partial

from app.audio_capture.application.dto.audio_capture import (
    AudioCaptureUploadResultDTO,
    BatchCreateAudioCaptureDTO,
    CreateAudioCaptureItemDTO,
)
from app.audio_capture.application.exceptions import (
    AudioCaptureArchiveEntryNotFoundException,
    AudioCaptureArchiveInvalidException,
)
from app.audio_capture.domain.command import CreateAudioCaptureCommand
from app.audio_capture.domain.entities.audio_capture import AudioCapture
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo
from app.audio_capture.domain.interfaces.services import IAudioAnalyzer
from app.shared_kernel.domain.command.file import AssignFileCommand
from app.shared_kernel.domain.interfaces.object_storage import IObjectStorageClient
from app.shared_kernel.domain.interfaces.services import IFileAnalyzer
from core.common.exceptions import CustomException
from core.db import Transactional
from core.db.transactional import on_rollback


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
    async def execute(self, *, data: BatchCreateAudioCaptureDTO) -> dict[str, AudioCaptureUploadResultDTO]:
        try:
            archive = zipfile.ZipFile(io.BytesIO(data.archive_file))
        except zipfile.BadZipFile as e:
            raise AudioCaptureArchiveInvalidException from e

        # 이미 저장된(firebase_anon_id, client_capture_id 조합이 동일한) 데이터 불러오기
        saved_client_capture_ids = await self._audio_capture_repo.get_existing_client_capture_ids(
            firebase_anon_uid=data.firebase_anon_uid,
            client_capture_ids=[item.client_capture_id for item in data.items],
        )

        results: dict[str, AudioCaptureUploadResultDTO] = {}
        with archive:
            for item in data.items:
                # 저장되어있으면 다시 저장하지 않고 패스
                if item.client_capture_id in saved_client_capture_ids:
                    results[item.client_capture_id] = AudioCaptureUploadResultDTO(status="success")
                    continue

                try:
                    await self._save_one(data=data, item=item, archive=archive)
                except CustomException as e:
                    results[item.client_capture_id] = AudioCaptureUploadResultDTO(
                        status="rejected",
                        code=e.code,
                        error_code=e.error_code,
                        message=e.message,
                    )
                    continue

                saved_client_capture_ids.add(item.client_capture_id)
                results[item.client_capture_id] = AudioCaptureUploadResultDTO(status="success")

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
            raise AudioCaptureArchiveEntryNotFoundException from e
        except zipfile.BadZipFile as e:
            raise AudioCaptureArchiveInvalidException from e

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
