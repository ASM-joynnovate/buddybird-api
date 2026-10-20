from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import (
    ActiveUser,
    DBSession,
    Locale,
    Storage,
    require_active_user,
    require_feed_reaction_type,
)
from app.models import FeedReactionType
from app.schemas.base import BaseResponse
from app.schemas.feed import FeedParams, FeedReactionTypeListResponse, FeedResponse
from app.services import feed

router = APIRouter(prefix="/feed")


@router.get("", name="피드 조회")
async def get_list(
    user: ActiveUser, query: Annotated[FeedParams, Query()], db: DBSession, storage: Storage
) -> FeedResponse:
    items, next_cursor = await feed.get_list(db=db, storage=storage, user=user, query=query)

    return FeedResponse(message="피드 조회 성공", data=items, meta={"next_cursor": next_cursor})


@router.get("/reaction-types", name="반응 종류 목록 조회", dependencies=[Depends(require_active_user)])
async def get_reaction_types(locale: Locale, db: DBSession, storage: Storage) -> FeedReactionTypeListResponse:
    return FeedReactionTypeListResponse(
        message="반응 종류 목록 조회 성공",
        data=await feed.get_reaction_types(db=db, storage=storage, locale=locale),
    )


@router.put("/{feed_item_id}/reactions/{reaction_type_id}", name="반응 남기기")
async def add_reaction(
    user: ActiveUser,
    feed_item_id: UUID,
    reaction_type: Annotated[FeedReactionType, Depends(require_feed_reaction_type)],
    db: DBSession,
) -> BaseResponse:
    await feed.add_reaction(db=db, user=user, feed_item_id=feed_item_id, reaction_type=reaction_type)

    return BaseResponse(message="반응 남기기 성공")


@router.delete("/{feed_item_id}/reactions/{reaction_type_id}", name="반응 삭제")
async def delete_reaction(user: ActiveUser, feed_item_id: UUID, reaction_type_id: UUID, db: DBSession) -> BaseResponse:
    await feed.delete_reaction(db=db, user=user, feed_item_id=feed_item_id, reaction_type_id=reaction_type_id)

    return BaseResponse(message="반응 삭제 성공")
