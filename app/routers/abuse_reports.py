from fastapi import APIRouter

from app.dependencies import ActiveUser, DBSession
from app.schemas.abuse_reports import CreateAbuseReportRequest
from app.schemas.base import BaseResponse
from app.services import abuse_reports

router = APIRouter(prefix="/abuse-reports")


@router.post("", name="신고")
async def create(user: ActiveUser, body: CreateAbuseReportRequest, db: DBSession) -> BaseResponse:
    await abuse_reports.create(db=db, user=user, data=body)

    return BaseResponse(message="신고 성공")
