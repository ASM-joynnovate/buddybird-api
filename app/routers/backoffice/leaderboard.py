from fastapi import APIRouter

from app.dependencies import DBSession
from app.schemas.leaderboard import ScoreBackfillResponse
from app.services import leaderboard

router = APIRouter(prefix="/leaderboard")


# 출시 후 한 번 호출하고 삭제할 API, 삭제할 때 leaderboard.backfill_score_entries와 ScoreBackfillDTO도 함께 삭제
@router.post("/score-entries/backfill", name="과거 세션 점수 채우기")
async def backfill_score_entries(db: DBSession) -> ScoreBackfillResponse:
    return ScoreBackfillResponse(
        message="과거 세션 점수 채우기 성공", data=await leaderboard.backfill_score_entries(db=db)
    )
