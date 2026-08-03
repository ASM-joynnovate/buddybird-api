from abc import ABC, abstractmethod
from uuid import UUID

from app.word.domain.entities.word import Word


class IWordRepo(ABC):
    @abstractmethod
    async def get_by_id(self, *, word_id: UUID) -> Word | None:
        pass

    @abstractmethod
    async def get_list(
        self,
        *,
        limit: int = 100,
        prev: int | None,
        label: str | None,
        user_id: str | None,
    ) -> list[Word]:
        pass

    @abstractmethod
    async def get_count(
        self,
        *,
        label: str | None,
        user_id: str | None,
    ) -> int:
        pass

    @abstractmethod
    async def exists(self, *, user_id: str, client_word_id: str) -> bool:
        pass

    @abstractmethod
    async def save(self, *, word: Word) -> None:
        pass
