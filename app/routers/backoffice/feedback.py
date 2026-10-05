from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import DBSession
from app.schemas.base import PageParams
from app.schemas.feedback import FeedbackListResponse
from app.services import feedback

router = APIRouter(prefix="/feedback")


@router.get("", name="피드백 목록 조회")
async def get_list(query: Annotated[PageParams, Query()], db: DBSession) -> FeedbackListResponse:
    items, total = await feedback.get_list(db=db, query=query)

    return FeedbackListResponse(
        message="피드백 목록 조회 성공",
        data=items,
        meta=query.meta(total),
    )
