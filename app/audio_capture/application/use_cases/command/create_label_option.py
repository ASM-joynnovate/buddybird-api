from uuid import UUID

from app.audio_capture.application.dto import CreateLabelOptionDTO
from app.audio_capture.application.errors import DuplicateLabelOptionError
from app.audio_capture.domain.commands import CreateLabelOptionCommand
from app.audio_capture.domain.entities.label import LabelOption
from app.audio_capture.domain.interfaces.repositories import ILabelCategoryRepo, ILabelOptionRepo
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class CreateLabelOptionUseCase:
    def __init__(
        self,
        *,
        label_category_repo: ILabelCategoryRepo,
        label_option_repo: ILabelOptionRepo,
    ):
        self._label_category_repo = label_category_repo
        self._label_option_repo = label_option_repo

    @Transactional()
    async def execute(self, *, label_category_id: UUID, data: CreateLabelOptionDTO) -> None:
        category = await self._label_category_repo.get_by_id(label_category_id=label_category_id)
        if category is None:
            raise ResourceNotFoundError

        if await self._label_option_repo.exists_by_category_id_and_name(category_id=label_category_id, name=data.name):
            raise DuplicateLabelOptionError

        option = LabelOption.create(
            command=CreateLabelOptionCommand(
                category_id=label_category_id, name=data.name, display_order=data.display_order
            )
        )

        await self._label_option_repo.save(label_option=option)
