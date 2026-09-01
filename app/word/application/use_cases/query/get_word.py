from uuid import UUID

from app.word.application.dto import GetWordDTO
from app.word.domain.interfaces.repositories import IWordRepo
from core.common.errors import ResourceNotFoundError


class GetWordUseCase:
    def __init__(
        self,
        *,
        word_repo: IWordRepo,
    ):
        self._word_repo = word_repo

    async def execute(self, *, word_id: UUID) -> GetWordDTO:
        word = await self._word_repo.get_by_id(word_id=word_id)
        if word is None:
            raise ResourceNotFoundError

        return GetWordDTO(
            id=word.id,
            label=word.label,
            firebase_anon_uid=word.firebase_anon_uid,
            client_word_id=word.client_word_id,
            device_platform=word.device_platform,
            device_os_version=word.device_os_version,
            device_model=word.device_model,
        )
