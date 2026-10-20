from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import DBSession, Storage, require_feed_item, require_feed_reaction_type
from app.models import FeedItem, FeedReactionType
from app.schemas.base import BaseResponse, ReorderRequest, UploadRequest, UploadResponse
from app.schemas.feed import (
    BackofficeFeedReactionTypeListResponse,
    BackofficeFeedReactionTypeResponse,
    CreateFeedReactionTypeRequest,
    UpdateFeedReactionTypeRequest,
)
from app.services import feed

router = APIRouter(prefix="/feed")


@router.get("/reaction-types", name="반응 종류 목록 조회")
async def get_reaction_types(db: DBSession, storage: Storage) -> BackofficeFeedReactionTypeListResponse:
    return BackofficeFeedReactionTypeListResponse(
        message="반응 종류 목록 조회 성공",
        data=await feed.get_backoffice_reaction_types(db=db, storage=storage),
    )


@router.post("/reaction-types", name="반응 종류 생성")
async def create_reaction_type(
    body: CreateFeedReactionTypeRequest, db: DBSession, storage: Storage
) -> BackofficeFeedReactionTypeResponse:
    return BackofficeFeedReactionTypeResponse(
        message="반응 종류 생성 성공",
        data=await feed.create_reaction_type(db=db, storage=storage, data=body),
    )


@router.post("/reaction-types/images", name="반응 종류 이미지 업로드 URL 발급")
async def add_reaction_type_image(body: UploadRequest, db: DBSession, storage: Storage) -> UploadResponse:
    return UploadResponse(
        message="반응 종류 이미지 업로드 URL 발급 성공",
        data=await feed.add_reaction_type_image(db=db, storage=storage, data=body),
    )


@router.patch("/reaction-types/{reaction_type_id}", name="반응 종류 수정")
async def update_reaction_type(
    reaction_type: Annotated[FeedReactionType, Depends(require_feed_reaction_type)],
    body: UpdateFeedReactionTypeRequest,
    db: DBSession,
    storage: Storage,
) -> BackofficeFeedReactionTypeResponse:
    return BackofficeFeedReactionTypeResponse(
        message="반응 종류 수정 성공",
        data=await feed.update_reaction_type(db=db, storage=storage, reaction_type=reaction_type, data=body),
    )


@router.put("/reaction-types/order", name="반응 종류 순서 변경")
async def reorder_reaction_types(
    body: ReorderRequest, db: DBSession, storage: Storage
) -> BackofficeFeedReactionTypeListResponse:
    return BackofficeFeedReactionTypeListResponse(
        message="반응 종류 순서 변경 성공",
        data=await feed.reorder_reaction_types(db=db, storage=storage, data=body),
    )


@router.delete("/reaction-types/{reaction_type_id}", name="반응 종류 삭제")
async def delete_reaction_type(
    reaction_type: Annotated[FeedReactionType, Depends(require_feed_reaction_type)], db: DBSession
) -> BaseResponse:
    await feed.delete_reaction_type(db=db, reaction_type=reaction_type)

    return BaseResponse(message="반응 종류 삭제 성공")


@router.post("/{feed_item_id}/hide", name="피드 항목 숨김")
async def hide(feed_item: Annotated[FeedItem, Depends(require_feed_item)], db: DBSession) -> BaseResponse:
    await feed.hide(db=db, feed_item=feed_item)

    return BaseResponse(message="피드 항목 숨김 성공")
