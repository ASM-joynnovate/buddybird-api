from uuid import UUID

from app.audio_capture.application.dto import UpdateAudioSegmentMemoDTO
from app.audio_capture.domain.commands import UpdateAudioSegmentMemoCommand
from app.audio_capture.domain.interfaces.repositories import IAudioSegmentRepo
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class UpdateAudioSegmentMemoUseCase:
    def __init__(
        self,
        *,
        audio_segment_repo: IAudioSegmentRepo,
    ):
        self._audio_segment_repo = audio_segment_repo

    @Transactional()
    async def execute(self, *, audio_segment_id: UUID, data: UpdateAudioSegmentMemoDTO) -> None:
        segment = await self._audio_segment_repo.get_by_id(audio_segment_id=audio_segment_id)
        if segment is None:
            raise ResourceNotFoundError

        segment.update_memo(command=UpdateAudioSegmentMemoCommand(memo=data.memo))
