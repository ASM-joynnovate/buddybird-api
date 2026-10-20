from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import ActiveUser, DBSession, Storage
from app.schemas.leaderboard import LeaderboardParams, LeaderboardResponse
from app.services import leaderboard

router = APIRouter(prefix="/leaderboard")


@router.get("", name="리더보드 조회")
async def get_leaderboard(
    user: ActiveUser, query: Annotated[LeaderboardParams, Query()], db: DBSession, storage: Storage
) -> LeaderboardResponse:
    return LeaderboardResponse(
        message="리더보드 조회 성공",
        data=await leaderboard.get_leaderboard(db=db, storage=storage, user=user, query=query),
    )
