from fastapi import APIRouter, Depends

from app.dependencies import require_active_user
from app.schemas.petcam import TurnCredentialResponse
from app.services import petcam

router = APIRouter(prefix="/petcam")


@router.post("/turn-credentials", name="펫캠 TURN 접속 정보 발급", dependencies=[Depends(require_active_user)])
async def issue_turn_credential() -> TurnCredentialResponse:
    return TurnCredentialResponse(message="펫캠 TURN 접속 정보 발급 성공", data=await petcam.issue_turn_credential())
