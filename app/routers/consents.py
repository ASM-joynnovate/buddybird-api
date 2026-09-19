from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import ActiveUser, DBSession, require_backoffice, require_consent
from app.models import Consent
from app.schemas.base import BaseResponse
from app.schemas.consents import ConsentListResponse, ConsentResponse, CreateConsentRequest, UpdateConsentRequest
from app.services import consents

router = APIRouter(prefix="/consents")


@router.get("", name="고지문 목록 조회", response_model=ConsentListResponse)
async def get_list(user: ActiveUser, db: DBSession) -> ConsentListResponse:
    return ConsentListResponse(message="고지문 목록 조회 성공", data=await consents.get_list(db=db, user=user))


@router.get("/{consent_id}", name="고지문 상세 조회", response_model=ConsentResponse)
async def get_detail(
    user: ActiveUser, consent: Annotated[Consent, Depends(require_consent)], db: DBSession
) -> ConsentResponse:
    return ConsentResponse(
        message="고지문 상세 조회 성공", data=await consents.get_detail(db=db, user=user, consent=consent)
    )


@router.post("", name="고지문 생성", response_model=ConsentResponse, dependencies=[Depends(require_backoffice)])
async def create(body: CreateConsentRequest, db: DBSession) -> ConsentResponse:
    return ConsentResponse(message="고지문 생성 성공", data=await consents.create(db=db, data=body))


@router.patch(
    "/{consent_id}", name="고지문 수정", response_model=ConsentResponse, dependencies=[Depends(require_backoffice)]
)
async def update(
    consent: Annotated[Consent, Depends(require_consent)], body: UpdateConsentRequest, db: DBSession
) -> ConsentResponse:
    return ConsentResponse(message="고지문 수정 성공", data=await consents.update(db=db, consent=consent, data=body))


@router.delete("/{consent_id}", name="고지문 삭제", dependencies=[Depends(require_backoffice)])
async def delete(consent: Annotated[Consent, Depends(require_consent)], db: DBSession) -> BaseResponse:
    await consents.delete(db=db, consent=consent)

    return BaseResponse(message="고지문 삭제 성공")
