from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import DBSession, Storage
from app.schemas.feedback import BackofficeFeedbackListParams, BackofficeFeedbackListResponse
from app.services import feedback

router = APIRouter(prefix="/feedback")


@router.get("", name="피드백 목록 조회")
async def get_list(
    query: Annotated[BackofficeFeedbackListParams, Query()], db: DBSession, storage: Storage
) -> BackofficeFeedbackListResponse:
    items, total = await feedback.get_backoffice_list(db=db, storage=storage, query=query)

    return BackofficeFeedbackListResponse(
        message="피드백 목록 조회 성공",
        data=items,
        meta={**query.meta(total), "total_count": total},
    )
