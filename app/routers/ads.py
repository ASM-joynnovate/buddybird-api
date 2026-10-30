from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import ActiveDevice, ActiveUser, DBSession, Locale, Storage
from app.schemas.ads import AddAdEventsRequest, AdListParams, HomeBannerAdListResponse
from app.schemas.base import BaseResponse
from app.services import ads

router = APIRouter(prefix="/ads")


@router.get("", name="광고 목록 조회")
async def get_list(
    user: ActiveUser, locale: Locale, query: Annotated[AdListParams, Query()], db: DBSession, storage: Storage
) -> HomeBannerAdListResponse:
    return HomeBannerAdListResponse(
        message="광고 목록 조회 성공",
        data=await ads.get_list(db=db, user=user, locale=locale, storage=storage, query=query),
    )


@router.post("/events", name="광고 이벤트 기록")
async def add_events(
    user: ActiveUser, device: ActiveDevice, locale: Locale, body: AddAdEventsRequest, db: DBSession
) -> BaseResponse:
    await ads.add_events(db=db, user=user, device=device, locale=locale, data=body)

    return BaseResponse(message="광고 이벤트 기록 성공")
