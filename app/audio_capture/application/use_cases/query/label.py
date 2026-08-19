from app.audio_capture.domain.entities.label import LabelCategory
from app.audio_capture.domain.interfaces.repositories import ILabelCategoryRepo


class LabelQueryUseCase:
    def __init__(self, *, label_category_repo: ILabelCategoryRepo):
        self._label_category_repo = label_category_repo

    async def get_list(self) -> list[LabelCategory]:
        return await self._label_category_repo.get_list()
