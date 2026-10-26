from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_or_404, transactional
from app.errors import SelfTargetError, UserSaveUnavailableError
from app.file import build_public_file_dto
from app.models import User, UserBlock
from app.s3 import S3StorageClient
from app.schemas.users import BlockedUserDTO


async def get_list(*, db: AsyncSession, storage: S3StorageClient, user: User) -> list[BlockedUserDTO]:
    stmt = (
        select(User)
        .join(UserBlock, UserBlock.blocked_user_id == User.id)
        .where(UserBlock.user_id == user.id)
        .order_by(UserBlock.created_at.desc())
    )
    blocked_users = (await db.scalars(stmt)).all()

    return [
        BlockedUserDTO(
            id=blocked_user.id,
            nickname=blocked_user.nickname,
            photo_file=build_public_file_dto(storage=storage, file=blocked_user.photo_file),
        )
        for blocked_user in blocked_users
    ]


@transactional(unavailable_error=UserSaveUnavailableError)
async def block(*, db: AsyncSession, user: User, blocked_user_id: UUID) -> None:
    if blocked_user_id == user.id:
        raise SelfTargetError

    await get_or_404(db=db, model=User, id=blocked_user_id)

    stmt = insert(UserBlock).values(user_id=user.id, blocked_user_id=blocked_user_id)

    await db.execute(stmt.on_conflict_do_nothing())


@transactional(unavailable_error=UserSaveUnavailableError)
async def unblock(*, db: AsyncSession, user: User, blocked_user_id: UUID) -> None:
    await db.execute(
        delete(UserBlock).where(UserBlock.user_id == user.id, UserBlock.blocked_user_id == blocked_user_id)
    )
