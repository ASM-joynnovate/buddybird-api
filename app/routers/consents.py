from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import ActiveUser, DBSession, Locale, require_consent
from app.models import Consent
from app.schemas.consents import ConsentListResponse, ConsentResponse
from app.services import consents

router = APIRouter(prefix="/consents")


@router.get("", name="고지문 목록 조회")
async def get_list(user: ActiveUser, locale: Locale, db: DBSession) -> ConsentListResponse:
    return ConsentListResponse(
        message="고지문 목록 조회 성공", data=await consents.get_list(db=db, user=user, locale=locale)
    )


@router.get("/{consent_id}", name="고지문 상세 조회")
async def get_detail(
    user: ActiveUser, locale: Locale, consent: Annotated[Consent, Depends(require_consent)], db: DBSession
) -> ConsentResponse:
    return ConsentResponse(
        message="고지문 상세 조회 성공",
        data=await consents.get_detail(db=db, user=user, locale=locale, consent=consent),
    )
