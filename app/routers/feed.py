from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies import ActiveUser, DBSession, Storage
from app.schemas.feed import FeedItemLikeResponse, FeedParams, FeedResponse
from app.services import feed

router = APIRouter(prefix="/feed")


@router.get("", name="피드 조회")
async def get_list(
    user: ActiveUser, query: Annotated[FeedParams, Query()], db: DBSession, storage: Storage
) -> FeedResponse:
    items, next_cursor = await feed.get_list(db=db, storage=storage, user=user, query=query)

    return FeedResponse(message="피드 조회 성공", data=items, meta={"next_cursor": next_cursor})


@router.put("/{feed_item_id}/like", name="좋아요")
async def like(user: ActiveUser, feed_item_id: UUID, db: DBSession) -> FeedItemLikeResponse:
    return FeedItemLikeResponse(
        message="좋아요 성공",
        data=await feed.like(db=db, user=user, feed_item_id=feed_item_id),
    )


@router.delete("/{feed_item_id}/like", name="좋아요 취소")
async def unlike(user: ActiveUser, feed_item_id: UUID, db: DBSession) -> FeedItemLikeResponse:
    return FeedItemLikeResponse(
        message="좋아요 취소 성공",
        data=await feed.unlike(db=db, user=user, feed_item_id=feed_item_id),
    )
