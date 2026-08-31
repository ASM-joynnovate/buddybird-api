from uuid import UUID

from app.audio_capture.domain.interfaces.repositories import (
    IAudioCaptureRepo,
    IAudioSegmentRepo,
    ILabelCategoryRepo,
)
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class DeleteLabelCategoryUseCase:
    def __init__(
        self,
        *,
        label_category_repo: ILabelCategoryRepo,
        audio_segment_repo: IAudioSegmentRepo,
        audio_capture_repo: IAudioCaptureRepo,
    ):
        self._label_category_repo = label_category_repo
        self._audio_segment_repo = audio_segment_repo
        self._audio_capture_repo = audio_capture_repo

    @Transactional()
    async def execute(self, *, label_category_id: UUID) -> None:
        category = await self._label_category_repo.get_by_id(label_category_id=label_category_id)
        if category is None:
            raise ResourceNotFoundError

        option_ids = [option.id for option in category.options]
        if option_ids:
            await self._audio_segment_repo.detach_label_options(label_option_ids=option_ids)
            await self._audio_capture_repo.detach_label_options(label_option_ids=option_ids)

        for option in category.options:
            option.delete()

        category.delete()
