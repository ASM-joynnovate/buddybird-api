from app.audio_capture.application.dto import CreateLabelCategoryDTO
from app.audio_capture.application.errors import DuplicateLabelCategoryError
from app.audio_capture.domain.commands import CreateLabelCategoryCommand
from app.audio_capture.domain.entities.label import LabelCategory
from app.audio_capture.domain.interfaces.repositories import ILabelCategoryRepo
from core.db import Transactional


class CreateLabelCategoryUseCase:
    def __init__(
        self,
        *,
        label_category_repo: ILabelCategoryRepo,
    ):
        self._label_category_repo = label_category_repo

    @Transactional()
    async def execute(self, *, data: CreateLabelCategoryDTO) -> None:
        if await self._label_category_repo.exists_by_name_and_target(name=data.name, target=data.target):
            raise DuplicateLabelCategoryError

        category = LabelCategory.create(
            command=CreateLabelCategoryCommand(name=data.name, display_order=data.display_order, target=data.target)
        )

        await self._label_category_repo.save(label_category=category)
