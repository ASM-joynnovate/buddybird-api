from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import DBSession, require_consent
from app.models import Consent
from app.schemas.base import BaseResponse
from app.schemas.consents import (
    BackofficeConsentListResponse,
    BackofficeConsentResponse,
    CreateConsentRequest,
    UpdateConsentRequest,
)
from app.services import consents

router = APIRouter(prefix="/consents")


@router.get("", name="고지문 목록 조회")
async def get_list(db: DBSession) -> BackofficeConsentListResponse:
    return BackofficeConsentListResponse(
        message="고지문 목록 조회 성공", data=await consents.get_backoffice_list(db=db)
    )


@router.post("", name="고지문 생성")
async def create(body: CreateConsentRequest, db: DBSession) -> BackofficeConsentResponse:
    return BackofficeConsentResponse(message="고지문 생성 성공", data=await consents.create(db=db, data=body))


@router.patch("/{consent_id}", name="고지문 수정")
async def update(
    consent: Annotated[Consent, Depends(require_consent)], body: UpdateConsentRequest, db: DBSession
) -> BackofficeConsentResponse:
    return BackofficeConsentResponse(
        message="고지문 수정 성공", data=await consents.update(db=db, consent=consent, data=body)
    )


@router.delete("/{consent_id}", name="고지문 삭제")
async def delete(consent: Annotated[Consent, Depends(require_consent)], db: DBSession) -> BaseResponse:
    await consents.delete(db=db, consent=consent)

    return BaseResponse(message="고지문 삭제 성공")
