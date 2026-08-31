from uuid import UUID

from app.audio_capture.application.dto import UpdateLabelOptionDTO
from app.audio_capture.domain.commands import UpdateLabelOptionCommand
from app.audio_capture.domain.interfaces.repositories import ILabelOptionRepo
from core.common.errors import ResourceNotFoundError
from core.db import Transactional


class UpdateLabelOptionUseCase:
    def __init__(
        self,
        *,
        label_option_repo: ILabelOptionRepo,
    ):
        self._label_option_repo = label_option_repo

    @Transactional()
    async def execute(self, *, label_option_id: UUID, data: UpdateLabelOptionDTO) -> None:
        option = await self._label_option_repo.get_by_id(label_option_id=label_option_id)
        if option is None:
            raise ResourceNotFoundError

        option.update(command=UpdateLabelOptionCommand(name=data.name, display_order=data.display_order))
