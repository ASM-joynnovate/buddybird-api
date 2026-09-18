from fastapi import APIRouter

from app.dependencies import ActiveUser, DBSession
from app.schemas.consents import ConsentListResponse, ConsentResponse, SaveConsentRequest
from app.services import consents

router = APIRouter(prefix="/users/me/consents")


@router.get("", name="동의 목록 조회", response_model=ConsentListResponse)
async def get_consents(user: ActiveUser, db: DBSession) -> ConsentListResponse:
    return ConsentListResponse(message="동의 목록 조회 성공", data=await consents.get_consents(db=db, user=user))


@router.post("", name="동의 기록", response_model=ConsentResponse)
async def save_consent(user: ActiveUser, body: SaveConsentRequest, db: DBSession) -> ConsentResponse:
    return ConsentResponse(message="동의 기록 성공", data=await consents.save_consent(db=db, user=user, data=body))
