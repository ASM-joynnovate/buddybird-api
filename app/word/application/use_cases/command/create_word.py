from functools import partial

from app.shared_kernel.domain.command.file import AssignFileCommand
from app.shared_kernel.domain.interfaces.object_storage import IObjectStorageClient
from app.shared_kernel.domain.interfaces.services import IFileAnalyzer
from app.word.application.dto.word import CreateWordDTO
from app.word.domain.command import CreateWordCommand
from app.word.domain.entities.word import Word
from app.word.domain.interfaces.repositories import IWordRepo
from core.db import Transactional
from core.db.transactional import on_rollback


class CreateWordUseCase:
    def __init__(
            self,
            *,
            object_storage_client: IObjectStorageClient,
            file_analyzer: IFileAnalyzer,
            word_repo: IWordRepo
    ):
        self._object_storage_client = object_storage_client
        self._file_analyzer = file_analyzer
        self._word_repo = word_repo

    @Transactional()
    async def execute(
            self,
            *,
            data: CreateWordDTO
    ) -> None:
        command = CreateWordCommand(
            label=data.label,
            firebase_anon_uid=data.firebase_anon_uid,
            audio_file=AssignFileCommand(
                name=data.audio_file.name,
                type=self._file_analyzer.get_mime_type(file=data.audio_file.file),
                file=data.audio_file.file,
            ),
            device_platform=data.device_platform,
            device_os_version=data.device_os_version,
            device_model=data.device_model,
        )

        word = Word.create(command=command)
        await self._word_repo.save(word=word)


        audio_file_path = f"{word.audio_file.file_path}/{word.audio_file.file_name}"
        on_rollback(partial(self._object_storage_client.delete, path=audio_file_path))
        await self._object_storage_client.upload(
            path=audio_file_path,
            file=data.audio_file.file,
        )