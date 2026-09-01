from uuid import UUID

from app.audio_capture.application.dto import UpdateLabelCategoryDTO
from app.audio_capture.domain.commands import UpdateLabelCategoryCommand
from app.audio_capture.domain.interfaces.repositories import ILabelCategoryRepo
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class UpdateLabelCategoryUseCase:
    def __init__(
        self,
        *,
        label_category_repo: ILabelCategoryRepo,
    ):
        self._label_category_repo = label_category_repo

    @Transactional()
    async def execute(self, *, label_category_id: UUID, data: UpdateLabelCategoryDTO) -> None:
        category = await self._label_category_repo.get_by_id(label_category_id=label_category_id)
        if category is None:
            raise ResourceNotFoundError

        category.update(command=UpdateLabelCategoryCommand(name=data.name, display_order=data.display_order))
