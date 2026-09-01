from app.audio_capture.application.dto import MigrateReviewResultDTO, MigrateReviewsDTO
from app.audio_capture.application.errors import DuplicateReviewAudioFileIdError
from app.audio_capture.domain.commands import (
    AssignAudioCaptureLabelsCommand,
    UpdateAudioCaptureMemoCommand,
)
from app.audio_capture.domain.entities.audio_capture import AudioCapture
from app.audio_capture.domain.entities.label import LabelOption
from app.audio_capture.domain.enums import LabelCategoryTargetEnum
from app.audio_capture.domain.interfaces.repositories import IAudioCaptureRepo, ILabelCategoryRepo
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class MigrateReviewsUseCase:
    def __init__(
        self,
        *,
        audio_capture_repo: IAudioCaptureRepo,
        label_category_repo: ILabelCategoryRepo,
    ):
        self._audio_capture_repo = audio_capture_repo
        self._label_category_repo = label_category_repo

    async def execute(self, *, data: MigrateReviewsDTO) -> dict[str, MigrateReviewResultDTO]:
        if not data.reviews:
            return {}

        if len(data.reviews) != len({review.audio_file_id for review in data.reviews}):
            raise DuplicateReviewAudioFileIdError

        valid_audio_file_paths = []
        for review in data.reviews:
            parts = review.audio_file_id.rsplit("/", 1)
            if len(parts) == 2:
                valid_audio_file_paths.append((parts[0], parts[1]))

        audio_file_paths = dict.fromkeys(valid_audio_file_paths)
        label_category_names = dict.fromkeys(label.category for review in data.reviews for label in review.label)

        audio_captures = {
            f"{audio_capture.audio_file.file_path}/{audio_capture.audio_file.file_name}": audio_capture
            for audio_capture in await self._audio_capture_repo.get_by_audio_file_paths(
                audio_file_paths=list(audio_file_paths)
            )
        }
        label_options = {
            (category.name, option.name): option
            for category in await self._label_category_repo.get_by_names_and_target(
                names=list(label_category_names),
                target=LabelCategoryTargetEnum.CAPTURE,
            )
            for option in category.options
        }

        results: dict[str, MigrateReviewResultDTO] = {}
        for review in data.reviews:
            audio_capture = audio_captures.get(review.audio_file_id)
            review_label_keys = dict.fromkeys((label.category, label.option) for label in review.label)
            if audio_capture is None or any(key not in label_options for key in review_label_keys):
                results[review.audio_file_id] = MigrateReviewResultDTO(
                    status="rejected",
                    code=ResourceNotFoundError.code,
                    error_code=ResourceNotFoundError.error_code,
                    message=ResourceNotFoundError.message,
                )
                continue

            review_label_options = [label_options[key] for key in review_label_keys]
            await self._migrate_review(
                audio_capture=audio_capture,
                label_options=review_label_options,
                memo=review.memo or None,
            )
            results[review.audio_file_id] = MigrateReviewResultDTO(status="success")

        return results

    @Transactional()
    async def _migrate_review(
        self,
        *,
        audio_capture: AudioCapture,
        label_options: list[LabelOption],
        memo: str | None,
    ) -> None:
        audio_capture.assign_labels(command=AssignAudioCaptureLabelsCommand(label_options=label_options))
        audio_capture.update_memo(command=UpdateAudioCaptureMemoCommand(memo=memo))
