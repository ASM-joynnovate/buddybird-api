from uuid import UUID

from app.audio_capture.application.dto.audio_capture import AssignAudioCaptureLabelsDTO
from app.audio_capture.domain.command.audio_capture import AssignAudioCaptureLabelsCommand
from app.audio_capture.domain.enum import LabelCategoryTargetEnum
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo, ILabelCategoryRepo, ILabelOptionRepo
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class AssignAudioCaptureLabelsUseCase:
    def __init__(
        self,
        *,
        audio_capture_repo: IAudioCaptureRepo,
        label_option_repo: ILabelOptionRepo,
        label_category_repo: ILabelCategoryRepo,
    ):
        self._audio_capture_repo = audio_capture_repo
        self._label_option_repo = label_option_repo
        self._label_category_repo = label_category_repo

    @Transactional()
    async def execute(self, *, audio_capture_id: UUID, data: AssignAudioCaptureLabelsDTO) -> None:
        capture = await self._audio_capture_repo.get_by_id(audio_capture_id=audio_capture_id)
        if capture is None:
            raise ResourceNotFoundError

        unique_ids = list(set(data.label_option_ids))

        if not unique_ids:
            capture.assign_labels(command=AssignAudioCaptureLabelsCommand(label_options=[]))
            return

        options = await self._label_option_repo.get_by_ids(label_option_ids=unique_ids)
        if len(options) != len(unique_ids):
            raise ResourceNotFoundError

        category_ids = list({option.category_id for option in options})
        categories = await self._label_category_repo.get_by_ids(label_category_ids=category_ids)
        for category in categories:
            category.ensure_target(target=LabelCategoryTargetEnum.CAPTURE)

        capture.assign_labels(command=AssignAudioCaptureLabelsCommand(label_options=options))
