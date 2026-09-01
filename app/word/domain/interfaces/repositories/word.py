from abc import ABC, abstractmethod
from uuid import UUID

from app.word.domain.entities.word import Word


class IWordRepo(ABC):
    @abstractmethod
    async def get_by_id(self, *, word_id: UUID) -> Word | None: ...

    @abstractmethod
    async def get_list(
        self,
        *,
        prev: int,
        limit: int,
        label: str | None,
        user_id: str | None,
    ) -> list[Word]: ...

    @abstractmethod
    async def get_count(
        self,
        *,
        label: str | None,
        user_id: str | None,
    ) -> int: ...

    @abstractmethod
    async def exists_by_user_id_and_client_word_id(self, *, user_id: str, client_word_id: str) -> bool: ...

    @abstractmethod
    async def save(self, *, word: Word) -> None: ...
