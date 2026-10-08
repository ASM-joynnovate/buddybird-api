from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import DBSession
from app.schemas.dashboard import DashboardLiveResponse, DashboardParams, DashboardResponse, UserDashboardResponse
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
