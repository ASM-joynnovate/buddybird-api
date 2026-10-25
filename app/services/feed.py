from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, and_, delete, false, func, or_, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import FeedSaveUnavailableError, ResourceNotFoundError
from app.file import build_public_file_dto
from app.models import FeedItem, FeedItemLike, Parrot, User, UserBlock, UserSetting
from app.s3 import S3StorageClient
from app.schemas.feed import FeedItemDTO, FeedItemLikeDTO, FeedParams
from app.schemas.parrots import CommunityParrotDTO
from app.schemas.users import CommunityUserDTO

PUBLIC_USER = and_(User.nickname.is_not(None), User.is_anonymous.is_(False))


def select_visible_items(user: User) -> Select:
    blocked = (
        select(UserBlock)
        .where(
            or_(
                and_(UserBlock.user_id == user.id, UserBlock.blocked_user_id == FeedItem.user_id),
                and_(UserBlock.user_id == FeedItem.user_id, UserBlock.blocked_user_id == user.id),
            )
        )
        .exists()
    )

    return (
        select(FeedItem)
        .join(User, User.id == FeedItem.user_id)
        .outerjoin(UserSetting, UserSetting.user_id == FeedItem.user_id)
        .where(
            or_(
                FeedItem.user_id == user.id,
                and_(func.coalesce(UserSetting.feed_enabled, true()), PUBLIC_USER, ~blocked),
            )
        )
    )


async def build_community_users(
    *, db: AsyncSession, storage: S3StorageClient, users: Sequence[User]
) -> dict[UUID, CommunityUserDTO]:
    stmt = select(Parrot).where(Parrot.user_id.in_({user.id for user in users})).order_by(Parrot.created_at)
    parrots = (await db.scalars(stmt)).all()

    return {
        user.id: CommunityUserDTO(
            id=user.id,
            nickname=user.nickname,
            photo_file=build_public_file_dto(storage=storage, file=user.photo_file),
            country=user.country,
            parrots=[
                CommunityParrotDTO(
                    name=parrot.name,
                    species=parrot.species,
                    photo_file=build_public_file_dto(storage=storage, file=parrot.photo_file),
                )
                for parrot in parrots
                if parrot.user_id == user.id
            ],
        )
        for user in users
    }


async def add_items(*, db: AsyncSession, user_id: UUID, now: datetime, items: list[dict]) -> None:
    if not items:
        return

    stmt = (
        select(User.id)
        .outerjoin(UserSetting, UserSetting.user_id == User.id)
        .where(User.id == user_id, PUBLIC_USER, func.coalesce(UserSetting.feed_enabled, true()))
    )

    if await db.scalar(stmt) is None:
        return

    values = [
        {
            "word_id": None,
            "word_name": None,
            "file_id": None,
            "threshold": None,
            **item,
            "user_id": user_id,
            "created_at": now,
            "is_deleted": False,
        }
        for item in items
    ]

    await db.execute(insert(FeedItem).values(values).on_conflict_do_nothing())


async def get_likes(*, db: AsyncSession, user: User, feed_item_ids: list[UUID]) -> dict[UUID, FeedItemLikeDTO]:
    stmt = (
        select(FeedItemLike.feed_item_id, func.count(), func.bool_or(FeedItemLike.user_id == user.id))
        .join(User, User.id == FeedItemLike.user_id)
        .where(FeedItemLike.feed_item_id.in_(feed_item_ids))
        .group_by(FeedItemLike.feed_item_id)
    )
    rows = (await db.execute(stmt)).all()

    like_counts = {feed_item_id: count for feed_item_id, count, _ in rows}
    liked_ids = {feed_item_id for feed_item_id, _, is_liked in rows if is_liked}

    return {
        feed_item_id: FeedItemLikeDTO(like_count=like_counts.get(feed_item_id, 0), is_liked=feed_item_id in liked_ids)
        for feed_item_id in feed_item_ids
    }


async def get_list(
    *, db: AsyncSession, storage: S3StorageClient, user: User, query: FeedParams
) -> tuple[list[FeedItemDTO], UUID | None]:
    stmt = select_visible_items(user).add_columns(
        User, func.coalesce(UserSetting.feed_recording_sharing_enabled, false())
    )

    if query.cursor is not None:
        stmt = stmt.where(FeedItem.id < query.cursor)

    if query.kind is not None:
        stmt = stmt.where(FeedItem.kind == query.kind)

    if query.country is not None:
        stmt = stmt.where(User.country == query.country)

    if query.user_id is not None:
        stmt = stmt.where(FeedItem.user_id == query.user_id)

    rows = (await db.execute(stmt.order_by(FeedItem.id.desc()).limit(query.count_by_page + 1))).all()

    next_cursor = rows[query.count_by_page - 1][0].id if len(rows) > query.count_by_page else None
    rows = rows[: query.count_by_page]

    users = await build_community_users(
        db=db,
        storage=storage,
        users=list({author.id: author for _, author, _ in rows}.values()),
    )

    likes = await get_likes(db=db, user=user, feed_item_ids=[item.id for item, _, _ in rows])

    items = [
        FeedItemDTO(
            id=item.id,
            kind=item.kind,
            created_at=item.created_at,
            user=users[author.id],
            word_name=item.word_name,
            file=build_public_file_dto(storage=storage, file=item.file) if recording_enabled else None,
            threshold=item.threshold,
            like_count=likes[item.id].like_count,
            is_liked=likes[item.id].is_liked,
        )
        for item, author, recording_enabled in rows
    ]

    return items, next_cursor


@transactional(unavailable_error=FeedSaveUnavailableError)
async def like(*, db: AsyncSession, user: User, feed_item_id: UUID) -> FeedItemLikeDTO:
    stmt = select_visible_items(user).where(FeedItem.id == feed_item_id)

    if await db.scalar(stmt) is None:
        raise ResourceNotFoundError

    stmt = insert(FeedItemLike).values(feed_item_id=feed_item_id, user_id=user.id)

    await db.execute(stmt.on_conflict_do_nothing())

    likes = await get_likes(db=db, user=user, feed_item_ids=[feed_item_id])

    return likes[feed_item_id]


@transactional(unavailable_error=FeedSaveUnavailableError)
async def unlike(*, db: AsyncSession, user: User, feed_item_id: UUID) -> FeedItemLikeDTO:
    stmt = delete(FeedItemLike).where(FeedItemLike.feed_item_id == feed_item_id, FeedItemLike.user_id == user.id)

    await db.execute(stmt)

    likes = await get_likes(db=db, user=user, feed_item_ids=[feed_item_id])

    return likes[feed_item_id]


@transactional(unavailable_error=FeedSaveUnavailableError)
async def hide(*, db: AsyncSession, feed_item: FeedItem) -> None:
    feed_item.is_deleted = True

    await db.flush()
