from app.audio_capture.application.dto import GetLabelCategoryDTO, GetLabelOptionDTO
from app.audio_capture.domain.interfaces.repositories import ILabelCategoryRepo


class GetLabelListUseCase:
    def __init__(
        self,
        *,
        label_category_repo: ILabelCategoryRepo,
    ):
        self._label_category_repo = label_category_repo

    async def execute(self) -> list[GetLabelCategoryDTO]:
        categories = await self._label_category_repo.get_list()
        return [
            GetLabelCategoryDTO(
                id=category.id,
                name=category.name,
                display_order=category.display_order,
                target=category.target,
                options=[
                    GetLabelOptionDTO(id=option.id, name=option.name, display_order=option.display_order)
                    for option in category.options
                ],
            )
            for category in categories
        ]
