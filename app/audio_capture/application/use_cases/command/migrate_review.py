from app.audio_capture.application.dto.audio_capture import MigrateReviewDTO
from app.audio_capture.domain.command.audio_capture import (
    AssignAudioCaptureLabelsCommand,
    UpdateAudioCaptureMemoCommand,
)
from app.audio_capture.domain.enum import LabelCategoryTargetEnum
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo, ILabelOptionRepo
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class MigrateReviewUseCase:
    def __init__(
        self,
        *,
        audio_capture_repo: IAudioCaptureRepo,
        label_option_repo: ILabelOptionRepo,
    ):
        self._audio_capture_repo = audio_capture_repo
        self._label_option_repo = label_option_repo

    @Transactional()
    async def execute(self, *, data: MigrateReviewDTO) -> None:
        parts = data.audio_file_id.rsplit("/", 1)
        if len(parts) != 2:
            raise ResourceNotFoundError

        file_path, file_name = parts

        capture = await self._audio_capture_repo.get_by_audio_file_path(file_path=file_path, file_name=file_name)
        if capture is None:
            raise ResourceNotFoundError

        unique_labels = list({(label.category, label.option) for label in data.label})

        options = []
        for category_name, option_name in unique_labels:
            label_option = await self._label_option_repo.get_by_category_name_and_option_name_and_target(
                category_name=category_name,
                option_name=option_name,
                target=LabelCategoryTargetEnum.CAPTURE,
            )
            if label_option is None:
                raise ResourceNotFoundError
            options.append(label_option)

        capture.assign_labels(command=AssignAudioCaptureLabelsCommand(label_options=options))
        capture.update_memo(command=UpdateAudioCaptureMemoCommand(memo=data.memo or None))
