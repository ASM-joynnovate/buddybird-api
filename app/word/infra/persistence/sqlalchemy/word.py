from uuid import UUID

from sqlalchemy import func, select

from app.word.domain.entities.word import Word
from app.word.domain.interfaces.repositories import IWordRepo
from core.db import session, session_factory


class WordSQLAlchemyRepo(IWordRepo):
    async def get_by_id(self, *, word_id: UUID) -> Word | None:
        stmt = select(Word).where(Word.id == word_id)

        result = await session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_list(
        self,
        *,
        prev: int,
        limit: int,
        label: str | None,
        user_id: str | None,
    ) -> list[Word]:
        async with session_factory() as read_session:
            stmt = select(Word)

            if label is not None:
                stmt = stmt.where(Word.label == label)
            if user_id is not None:
                stmt = stmt.where(Word.firebase_anon_uid == user_id)

            stmt = stmt.order_by(Word.created_at.desc()).offset(prev).limit(limit)

            result = await read_session.execute(stmt)

            return list(result.scalars().all())

    async def get_count(
        self,
        *,
        label: str | None,
        user_id: str | None,
    ) -> int:
        async with session_factory() as read_session:
            stmt = select(func.count()).select_from(Word)

            if label is not None:
                stmt = stmt.where(Word.label == label)
            if user_id is not None:
                stmt = stmt.where(Word.firebase_anon_uid == user_id)

            result = await read_session.execute(stmt)

            return result.scalar_one()

    async def exists_by_user_id_and_client_word_id(self, *, user_id: str, client_word_id: str) -> bool:
        async with session_factory() as read_session:
            stmt = (
                select(Word.id)
                .where(Word.firebase_anon_uid == user_id)
                .where(Word.client_word_id == client_word_id)
                .limit(1)
            )

            result = await read_session.execute(stmt)

            return result.scalar_one_or_none() is not None

    async def save(self, *, word: Word) -> None:
        session.add(word)
