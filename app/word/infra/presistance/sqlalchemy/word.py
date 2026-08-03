from uuid import UUID

from sqlalchemy import func, select

from app.word.domain.entities.word import Word
from app.word.domain.interfaces.repositories import IWordRepo
from core.db import session, session_factory


class WordSQLAlchemyRepo(IWordRepo):
    async def get_by_id(self, *, word_id: UUID) -> Word | None:
        async with session_factory() as read_session:
            stmt = await read_session.execute(select(Word).where(Word.id == word_id).where(Word.is_deleted.is_(False)))

            return stmt.scalar_one_or_none()

    async def get_list(
        self,
        *,
        limit: int = 100,
        prev: int | None = None,
        label: str | None = None,
        user_id: str | None = None,
    ) -> list[Word]:
        async with session_factory() as read_session:
            stmt = select(Word).where(Word.is_deleted.is_(False))

            if label is not None:
                stmt = stmt.where(Word.label == label)
            if user_id is not None:
                stmt = stmt.where(Word.firebase_anon_uid == user_id)

            if prev is not None:
                stmt = stmt.offset(prev)
            stmt = stmt.limit(limit)

            result = await read_session.execute(stmt)
            return result.scalars().all()

    async def get_count(
        self,
        *,
        label: str | None,
        user_id: str | None,
    ) -> int:
        async with session_factory() as read_session:
            stmt = select(func.count()).where(Word.is_deleted.is_(False)).where(Word.firebase_anon_uid == user_id)

            if label is not None:
                stmt = stmt.where(Word.label == label)
            if user_id is not None:
                stmt = stmt.where(Word.firebase_anon_uid == user_id)

            result = await read_session.execute(stmt)
            return result.scalar_one()

    async def exists(self, *, user_id: str, client_word_id: str) -> bool:
        async with session_factory() as read_session:
            stmt = (
                select(Word)
                .where(Word.is_deleted.is_(False))
                .where(Word.firebase_anon_uid == user_id)
                .where(Word.client_word_id == client_word_id)
            )

            result = await read_session.execute(stmt)
            return result.scalar_one_or_none()

    async def save(self, *, word: Word) -> None:
        session.add(word)
