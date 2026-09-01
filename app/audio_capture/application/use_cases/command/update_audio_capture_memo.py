from uuid import UUID

from app.audio_capture.application.dto import UpdateAudioCaptureMemoDTO
from app.audio_capture.domain.commands import UpdateAudioCaptureMemoCommand
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class UpdateAudioCaptureMemoUseCase:
    def __init__(
        self,
        *,
        audio_capture_repo: IAudioCaptureRepo,
    ):
        self._audio_capture_repo = audio_capture_repo

    @Transactional()
    async def execute(self, *, audio_capture_id: UUID, data: UpdateAudioCaptureMemoDTO) -> None:
        capture = await self._audio_capture_repo.get_by_id(audio_capture_id=audio_capture_id)
        if capture is None:
            raise ResourceNotFoundError

        capture.update_memo(command=UpdateAudioCaptureMemoCommand(memo=data.memo))
