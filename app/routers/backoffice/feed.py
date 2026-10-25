from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import DBSession, require_feed_item
from app.models import FeedItem
from app.schemas.base import BaseResponse
from app.services import feed

router = APIRouter(prefix="/feed")


@router.post("/{feed_item_id}/hide", name="피드 항목 숨김")
async def hide(feed_item: Annotated[FeedItem, Depends(require_feed_item)], db: DBSession) -> BaseResponse:
    await feed.hide(db=db, feed_item=feed_item)

    return BaseResponse(message="피드 항목 숨김 성공")
