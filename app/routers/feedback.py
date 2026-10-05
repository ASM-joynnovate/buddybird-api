from fastapi import APIRouter

from app.dependencies import ActiveDevice, ActiveUser, DBSession
from app.schemas.feedback import CreateFeedbackRequest, FeedbackResponse
from app.services import feedback

router = APIRouter(prefix="/feedback")


@router.post("", name="피드백 제출")
async def create(
    user: ActiveUser, device: ActiveDevice, body: CreateFeedbackRequest, db: DBSession
) -> FeedbackResponse:
    return FeedbackResponse(
        message="피드백 제출 성공", data=await feedback.create(db=db, user=user, device=device, data=body)
    )
