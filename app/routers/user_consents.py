from fastapi import APIRouter

from app.dependencies import ActiveUser, DBSession
from app.schemas.consents import SaveUserConsentRequest, UserConsentListResponse, UserConsentResponse
from app.services import user_consents

router = APIRouter(prefix="/users/me/consents")


@router.get("", name="동의 목록 조회", response_model=UserConsentListResponse)
async def get_list(user: ActiveUser, db: DBSession) -> UserConsentListResponse:
    return UserConsentListResponse(message="동의 목록 조회 성공", data=await user_consents.get_list(db=db, user=user))


@router.post("", name="동의 기록", response_model=UserConsentResponse)
async def save(user: ActiveUser, body: SaveUserConsentRequest, db: DBSession) -> UserConsentResponse:
    return UserConsentResponse(message="동의 기록 성공", data=await user_consents.save(db=db, user=user, data=body))
