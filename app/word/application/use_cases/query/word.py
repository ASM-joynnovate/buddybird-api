from uuid import UUID

from app.word.domain.entities.word import Word
from app.word.domain.interfaces.repositories import IWordRepo
from core.common.exceptions import ResourceNotFoundException


class WordQueryUseCase:
    def __init__(
            self,
            *,
            word_repo: IWordRepo,
    ):
        self._word_repo = word_repo

    async def get_by_id(
            self,
            *,
            word_id: UUID
    ) -> Word:
        word = await self._word_repo.get_by_id(word_id=word_id)
        if not word:
            raise ResourceNotFoundException

        return word