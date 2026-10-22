from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid7

from pydantic.experimental.missing_sentinel import MISSING
from sqlalchemy import Select, and_, delete, false, func, or_, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_or_404, transactional
from app.enums import FileStatusEnum, LocaleEnum
from app.errors import (
    FeedReactionTypeOrderMismatchError,
    FeedSaveUnavailableError,
    FileSizeExceededError,
    InvalidFeedReactionTypeImageError,
    ResourceNotFoundError,
)
from app.file import build_file_dto, build_public_file_dto
from app.models import (
    FeedItem,
    FeedItemReaction,
    FeedReactionType,
    File,
    I18n,
    Parrot,
    User,
    UserBlock,
    UserSetting,
)
from app.s3 import S3StorageClient
from app.schemas.base import I18nDTO, ReorderRequest, UploadDTO, UploadRequest
from app.schemas.feed import (
    BackofficeFeedReactionTypeDTO,
    CreateFeedReactionTypeRequest,
    FeedItemDTO,
    FeedItemReactionDTO,
    FeedParams,
    FeedReactionTypeDTO,
    UpdateFeedReactionTypeRequest,
)
from app.schemas.parrots import CommunityParrotDTO
from app.schemas.users import CommunityUserDTO
from app.utils import MAX_PHOTO_BYTES

PUBLIC_USER = and_(User.nickname.is_not(None), User.is_anonymous.is_(False))
REACTION_TYPE_IMAGE_NAMES = {"image/png": "image.png", "image/jpeg": "image.jpg", "image/svg+xml": "image.svg"}


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


def build_backoffice_reaction_type_dto(
    reaction_type: FeedReactionType, storage: S3StorageClient
) -> BackofficeFeedReactionTypeDTO:
    return BackofficeFeedReactionTypeDTO(
        id=reaction_type.id,
        name=I18nDTO.model_validate(reaction_type.name_i18n, from_attributes=True),
        image_file=build_file_dto(storage=storage, file=reaction_type.image_file),
        sort_order=reaction_type.sort_order,
    )


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


async def get_reactions(
    *, db: AsyncSession, user: User, feed_item_ids: list[UUID]
) -> dict[UUID, list[FeedItemReactionDTO]]:
    stmt = (
        select(
            FeedItemReaction.feed_item_id,
            FeedItemReaction.reaction_type_id,
            func.count(),
            func.bool_or(FeedItemReaction.user_id == user.id),
        )
        .join(User, User.id == FeedItemReaction.user_id)
        .join(FeedReactionType, FeedReactionType.id == FeedItemReaction.reaction_type_id)
        .where(FeedItemReaction.feed_item_id.in_(feed_item_ids))
        .group_by(FeedItemReaction.feed_item_id, FeedItemReaction.reaction_type_id, FeedReactionType.sort_order)
        .order_by(FeedReactionType.sort_order)
    )
    reactions: dict[UUID, list[FeedItemReactionDTO]] = {}

    for feed_item_id, reaction_type_id, count, is_mine in (await db.execute(stmt)).all():
        reactions.setdefault(feed_item_id, []).append(
            FeedItemReactionDTO(reaction_type_id=reaction_type_id, count=count, is_mine=is_mine)
        )

    return reactions


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

    reactions = await get_reactions(db=db, user=user, feed_item_ids=[item.id for item, _, _ in rows])

    items = [
        FeedItemDTO(
            id=item.id,
            kind=item.kind,
            created_at=item.created_at,
            user=users[author.id],
            word_name=item.word_name,
            file=build_public_file_dto(storage=storage, file=item.file) if recording_enabled else None,
            threshold=item.threshold,
            reactions=reactions.get(item.id, []),
        )
        for item, author, recording_enabled in rows
    ]

    return items, next_cursor


@transactional(unavailable_error=FeedSaveUnavailableError)
async def add_reaction(
    *, db: AsyncSession, user: User, feed_item_id: UUID, reaction_type: FeedReactionType
) -> list[FeedItemReactionDTO]:
    stmt = select_visible_items(user).where(FeedItem.id == feed_item_id)

    if await db.scalar(stmt) is None:
        raise ResourceNotFoundError

    stmt = insert(FeedItemReaction).values(
        feed_item_id=feed_item_id,
        user_id=user.id,
        reaction_type_id=reaction_type.id,
    )

    await db.execute(stmt.on_conflict_do_nothing())

    reactions = await get_reactions(db=db, user=user, feed_item_ids=[feed_item_id])

    return reactions.get(feed_item_id, [])


@transactional(unavailable_error=FeedSaveUnavailableError)
async def delete_reaction(
    *, db: AsyncSession, user: User, feed_item_id: UUID, reaction_type_id: UUID
) -> list[FeedItemReactionDTO]:
    await db.execute(
        delete(FeedItemReaction).where(
            FeedItemReaction.feed_item_id == feed_item_id,
            FeedItemReaction.user_id == user.id,
            FeedItemReaction.reaction_type_id == reaction_type_id,
        )
    )

    reactions = await get_reactions(db=db, user=user, feed_item_ids=[feed_item_id])

    return reactions.get(feed_item_id, [])


@transactional(unavailable_error=FeedSaveUnavailableError)
async def hide(*, db: AsyncSession, feed_item: FeedItem) -> None:
    feed_item.is_deleted = True

    await db.flush()


async def get_reaction_types(
    *, db: AsyncSession, storage: S3StorageClient, locale: LocaleEnum
) -> list[FeedReactionTypeDTO]:
    stmt = (
        select(FeedReactionType)
        .join(File, File.id == FeedReactionType.image_file_id)
        .where(File.status == FileStatusEnum.UPLOADED.value)
        .order_by(FeedReactionType.sort_order)
    )
    reaction_types = (await db.scalars(stmt)).all()

    return [
        FeedReactionTypeDTO(
            id=reaction_type.id,
            name=reaction_type.name_i18n.get_text(locale),
            image_file=build_public_file_dto(storage=storage, file=reaction_type.image_file),
        )
        for reaction_type in reaction_types
    ]


async def get_backoffice_reaction_types(
    *, db: AsyncSession, storage: S3StorageClient
) -> list[BackofficeFeedReactionTypeDTO]:
    stmt = select(FeedReactionType).order_by(FeedReactionType.sort_order)
    reaction_types = (await db.scalars(stmt)).all()

    return [build_backoffice_reaction_type_dto(reaction_type, storage) for reaction_type in reaction_types]


@transactional(unavailable_error=FeedSaveUnavailableError)
async def add_reaction_type_image(*, db: AsyncSession, storage: S3StorageClient, data: UploadRequest) -> UploadDTO:
    if data.content_type not in REACTION_TYPE_IMAGE_NAMES:
        raise InvalidFeedReactionTypeImageError

    if data.file_size > MAX_PHOTO_BYTES:
        raise FileSizeExceededError

    file_id = uuid7()

    image_file = File(
        id=file_id,
        file_name=REACTION_TYPE_IMAGE_NAMES[data.content_type],
        file_path=f"feed/reaction-types/{file_id}",
        file_size=data.file_size,
        file_type=data.content_type,
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )

    db.add(image_file)

    await db.flush()

    return storage.generate_presigned_upload(
        file_id=file_id,
        path=f"upload/{image_file.object_key}",
        content_type=data.content_type,
        file_size=data.file_size,
    )


@transactional(unavailable_error=FeedSaveUnavailableError)
async def create_reaction_type(
    *, db: AsyncSession, storage: S3StorageClient, data: CreateFeedReactionTypeRequest
) -> BackofficeFeedReactionTypeDTO:
    image_file = await get_or_404(db=db, model=File, id=data.image_file_id)

    stmt = select(func.coalesce(func.max(FeedReactionType.sort_order) + 1, 0))
    sort_order = await db.scalar(stmt)

    reaction_type = FeedReactionType(
        name_i18n=I18n(**data.name.model_dump()),
        image_file=image_file,
        sort_order=sort_order,
        is_deleted=False,
    )

    db.add(reaction_type)
    await db.flush()

    return build_backoffice_reaction_type_dto(reaction_type, storage)


@transactional(unavailable_error=FeedSaveUnavailableError)
async def update_reaction_type(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    reaction_type: FeedReactionType,
    data: UpdateFeedReactionTypeRequest,
) -> BackofficeFeedReactionTypeDTO:
    if data.name is not MISSING:
        for name, value in data.name.model_dump(exclude_unset=True).items():
            setattr(reaction_type.name_i18n, name, value)

    if data.image_file_id is not MISSING and data.image_file_id != reaction_type.image_file_id:
        old_file = reaction_type.image_file

        reaction_type.image_file = await get_or_404(db=db, model=File, id=data.image_file_id)
        old_file.is_deleted = True

    await db.flush()

    return build_backoffice_reaction_type_dto(reaction_type, storage)


@transactional(unavailable_error=FeedSaveUnavailableError)
async def reorder_reaction_types(
    *, db: AsyncSession, storage: S3StorageClient, data: ReorderRequest
) -> list[BackofficeFeedReactionTypeDTO]:
    stmt = select(FeedReactionType)
    reaction_types = {reaction_type.id: reaction_type for reaction_type in (await db.scalars(stmt)).all()}

    if sorted(data.ids) != sorted(reaction_types):
        raise FeedReactionTypeOrderMismatchError

    for sort_order, reaction_type_id in enumerate(data.ids):
        reaction_types[reaction_type_id].sort_order = sort_order

    await db.flush()

    return [
        build_backoffice_reaction_type_dto(reaction_types[reaction_type_id], storage) for reaction_type_id in data.ids
    ]


@transactional(unavailable_error=FeedSaveUnavailableError)
async def delete_reaction_type(*, db: AsyncSession, reaction_type: FeedReactionType) -> None:
    reaction_type.is_deleted = True

    await db.flush()
