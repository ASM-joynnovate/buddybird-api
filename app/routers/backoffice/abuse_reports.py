from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import DBSession, Storage, require_abuse_report
from app.models import AbuseReport
from app.schemas.abuse_reports import BackofficeAbuseReportListParams, BackofficeAbuseReportListResponse
from app.schemas.base import BaseResponse
from app.services import abuse_reports

router = APIRouter(prefix="/abuse-reports")


@router.get("", name="신고 목록 조회")
async def get_list(
    query: Annotated[BackofficeAbuseReportListParams, Query()], db: DBSession, storage: Storage
) -> BackofficeAbuseReportListResponse:
    items, total = await abuse_reports.get_backoffice_list(db=db, storage=storage, query=query)

    return BackofficeAbuseReportListResponse(
        message="신고 목록 조회 성공",
        data=items,
        meta={**query.meta(total), "total_count": total},
    )


@router.post("/{abuse_report_id}/handle", name="신고 처리 완료")
async def handle(abuse_report: Annotated[AbuseReport, Depends(require_abuse_report)], db: DBSession) -> BaseResponse:
    await abuse_reports.handle(db=db, abuse_report=abuse_report)

    return BaseResponse(message="신고 처리 완료 성공")
