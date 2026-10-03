from typing import Annotated

from fastapi import APIRouter, Header, Query

from app.dependencies import ActiveUser, DBSession
from app.schemas.reports import ReportParams, ReportResponse
from app.services import reports

router = APIRouter(prefix="/reports")


@router.get("", name="리포트 조회")
async def get_report(
    user: ActiveUser,
    query: Annotated[ReportParams, Query()],
    x_timezone: Annotated[str, Header(alias="X-Timezone")],
    db: DBSession,
) -> ReportResponse:
    return ReportResponse(
        message="리포트 조회 성공",
        data=await reports.get_report(db=db, user=user, query=query, timezone=x_timezone),
    )
