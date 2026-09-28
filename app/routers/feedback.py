from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import ActiveDevice, ActiveUser, DBSession, require_backoffice
from app.schemas.base import PageParams
from app.schemas.feedback import CreateFeedbackRequest, FeedbackListResponse, FeedbackResponse
from app.services import feedback

router = APIRouter(prefix="/feedback")


@router.post("", name="피드백 제출")
async def create(
    user: ActiveUser, device: ActiveDevice, body: CreateFeedbackRequest, db: DBSession
) -> FeedbackResponse:
    return FeedbackResponse(
        message="피드백 제출 성공", data=await feedback.create(db=db, user=user, device=device, data=body)
    )


@router.get("", name="피드백 목록 조회", dependencies=[Depends(require_backoffice)])
async def get_list(query: Annotated[PageParams, Query()], db: DBSession) -> FeedbackListResponse:
    items, total = await feedback.get_list(db=db, query=query)

    return FeedbackListResponse(
        message="피드백 목록 조회 성공",
        data=items,
        meta=query.meta(total),
    )
