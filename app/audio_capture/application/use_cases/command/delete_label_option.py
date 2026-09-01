from uuid import UUID

from app.audio_capture.domain.interfaces.repositories import (
    IAudioCaptureRepo,
    IAudioSegmentRepo,
    ILabelOptionRepo,
)
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class DeleteLabelOptionUseCase:
    def __init__(
        self,
        *,
        label_option_repo: ILabelOptionRepo,
        audio_segment_repo: IAudioSegmentRepo,
        audio_capture_repo: IAudioCaptureRepo,
    ):
        self._label_option_repo = label_option_repo
        self._audio_segment_repo = audio_segment_repo
        self._audio_capture_repo = audio_capture_repo

    @Transactional()
    async def execute(self, *, label_option_id: UUID) -> None:
        option = await self._label_option_repo.get_by_id(label_option_id=label_option_id)
        if option is None:
            raise ResourceNotFoundError

        await self._audio_segment_repo.detach_label_options(label_option_ids=[label_option_id])
        await self._audio_capture_repo.detach_label_options(label_option_ids=[label_option_id])

        option.delete()
