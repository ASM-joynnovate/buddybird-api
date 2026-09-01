from uuid import UUID

from app.audio_capture.application.dto import AssignAudioSegmentLabelDTO
from app.audio_capture.domain.commands import AssignAudioSegmentLabelCommand
from app.audio_capture.domain.enums import LabelCategoryTargetEnum
from app.audio_capture.domain.interfaces.repositories import (
    IAudioSegmentRepo,
    ILabelCategoryRepo,
    ILabelOptionRepo,
)
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class AssignAudioSegmentLabelUseCase:
    def __init__(
        self,
        *,
        audio_segment_repo: IAudioSegmentRepo,
        label_option_repo: ILabelOptionRepo,
        label_category_repo: ILabelCategoryRepo,
    ):
        self._audio_segment_repo = audio_segment_repo
        self._label_option_repo = label_option_repo
        self._label_category_repo = label_category_repo

    @Transactional()
    async def execute(self, *, audio_segment_id: UUID, data: AssignAudioSegmentLabelDTO) -> None:
        segment = await self._audio_segment_repo.get_by_id(audio_segment_id=audio_segment_id)
        if segment is None:
            raise ResourceNotFoundError

        option = await self._label_option_repo.get_by_id(label_option_id=data.label_option_id)
        if option is None:
            raise ResourceNotFoundError

        category = await self._label_category_repo.get_by_id(label_category_id=option.category_id)
        if category is None:
            raise ResourceNotFoundError
        category.ensure_target(target=LabelCategoryTargetEnum.SEGMENT)

        segment.assign_label(command=AssignAudioSegmentLabelCommand(label_option_id=data.label_option_id))
