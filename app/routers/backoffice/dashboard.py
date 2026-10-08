from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import DBSession
from app.schemas.dashboard import (
    AppUpdateDashboardParams,
    AppUpdateDashboardResponse,
    DashboardLiveResponse,
    DashboardParams,
    DashboardResponse,
    FeedbackDashboardResponse,
    NotificationDashboardResponse,
    UserDashboardResponse,
    WithdrawalDashboardResponse,
)
from app.services import dashboard

router = APIRouter(prefix="/dashboard")


@router.get("", name="대시보드 조회")
async def get_dashboard(query: Annotated[DashboardParams, Query()], db: DBSession) -> DashboardResponse:
    return DashboardResponse(
        message="대시보드 조회 성공",
        data=await dashboard.get_dashboard(db=db, query=query),
    )


@router.get("/live", name="대시보드 현재 상태 조회")
async def get_live(db: DBSession) -> DashboardLiveResponse:
    return DashboardLiveResponse(
        message="대시보드 현재 상태 조회 성공",
        data=await dashboard.get_live(db=db),
    )


@router.get("/users", name="사용자 대시보드 조회")
async def get_user_dashboard(query: Annotated[DashboardParams, Query()], db: DBSession) -> UserDashboardResponse:
    return UserDashboardResponse(
        message="사용자 대시보드 조회 성공",
        data=await dashboard.get_user_dashboard(db=db, query=query),
    )


@router.get("/feedback", name="피드백 대시보드 조회")
async def get_feedback_dashboard(
    query: Annotated[DashboardParams, Query()], db: DBSession
) -> FeedbackDashboardResponse:
    return FeedbackDashboardResponse(
        message="피드백 대시보드 조회 성공",
        data=await dashboard.get_feedback_dashboard(db=db, query=query),
    )


@router.get("/withdrawals", name="탈퇴 대시보드 조회")
async def get_withdrawal_dashboard(
    query: Annotated[DashboardParams, Query()], db: DBSession
) -> WithdrawalDashboardResponse:
    return WithdrawalDashboardResponse(
        message="탈퇴 대시보드 조회 성공",
        data=await dashboard.get_withdrawal_dashboard(db=db, query=query),
    )


@router.get("/notifications", name="알림 대시보드 조회")
async def get_notification_dashboard(
    query: Annotated[DashboardParams, Query()], db: DBSession
) -> NotificationDashboardResponse:
    return NotificationDashboardResponse(
        message="알림 대시보드 조회 성공",
        data=await dashboard.get_notification_dashboard(db=db, query=query),
    )


@router.get("/app-updates", name="앱 업데이트 대시보드 조회")
async def get_app_update_dashboard(
    query: Annotated[AppUpdateDashboardParams, Query()], db: DBSession
) -> AppUpdateDashboardResponse:
    return AppUpdateDashboardResponse(
        message="앱 업데이트 대시보드 조회 성공",
        data=await dashboard.get_app_update_dashboard(db=db, query=query),
    )
