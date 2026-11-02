from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import DBSession, Storage, require_ad
from app.models import Ad
from app.schemas.ads import (
    AdImageUploadRequest,
    BackofficeAdListParams,
    BackofficeAdListResponse,
    BackofficeAdResponse,
    BackofficeAdStatsParams,
    BackofficeAdStatsResponse,
    BackofficeAdTotalStatsResponse,
    CreateAdRequest,
    UpdateAdRequest,
)
from app.schemas.base import BaseResponse, ReorderRequest, UploadResponse
from app.services import ads

router = APIRouter(prefix="/ads")


@router.get("", name="광고 목록 조회")
async def get_list(
    query: Annotated[BackofficeAdListParams, Query()], db: DBSession, storage: Storage
) -> BackofficeAdListResponse:
    items, total = await ads.get_backoffice_list(db=db, storage=storage, query=query)

    return BackofficeAdListResponse(message="광고 목록 조회 성공", data=items, meta=query.meta(total))


@router.post("", name="광고 생성")
async def create(body: CreateAdRequest, db: DBSession, storage: Storage) -> BackofficeAdResponse:
    return BackofficeAdResponse(message="광고 생성 성공", data=await ads.create(db=db, storage=storage, data=body))


@router.put("/order", name="홈 배너 순서 변경")
async def reorder(body: ReorderRequest, db: DBSession, storage: Storage) -> BackofficeAdListResponse:
    return BackofficeAdListResponse(
        message="홈 배너 순서 변경 성공", data=await ads.reorder(db=db, storage=storage, data=body)
    )


@router.post("/images", name="광고 사진 업로드 URL 발급")
async def add_image(body: AdImageUploadRequest, db: DBSession, storage: Storage) -> UploadResponse:
    return UploadResponse(
        message="광고 사진 업로드 URL 발급 성공", data=await ads.add_image(db=db, storage=storage, data=body)
    )


@router.get("/stats", name="광고 전체 통계 조회")
async def get_total_stats(
    query: Annotated[BackofficeAdStatsParams, Query()], db: DBSession
) -> BackofficeAdTotalStatsResponse:
    return BackofficeAdTotalStatsResponse(
        message="광고 전체 통계 조회 성공", data=await ads.get_total_stats(db=db, query=query)
    )


@router.get("/{ad_id}", name="광고 상세 조회")
async def get_detail(ad: Annotated[Ad, Depends(require_ad)], db: DBSession, storage: Storage) -> BackofficeAdResponse:
    return BackofficeAdResponse(message="광고 상세 조회 성공", data=await ads.get_detail(db=db, storage=storage, ad=ad))


@router.patch("/{ad_id}", name="광고 수정")
async def update(
    ad: Annotated[Ad, Depends(require_ad)], body: UpdateAdRequest, db: DBSession, storage: Storage
) -> BackofficeAdResponse:
    return BackofficeAdResponse(
        message="광고 수정 성공", data=await ads.update(db=db, storage=storage, ad=ad, data=body)
    )


@router.delete("/{ad_id}", name="광고 삭제")
async def delete(ad: Annotated[Ad, Depends(require_ad)], db: DBSession) -> BaseResponse:
    await ads.delete(db=db, ad=ad)

    return BaseResponse(message="광고 삭제 성공")


@router.get("/{ad_id}/stats", name="광고 통계 조회")
async def get_stats(
    ad: Annotated[Ad, Depends(require_ad)], query: Annotated[BackofficeAdStatsParams, Query()], db: DBSession
) -> BackofficeAdStatsResponse:
    return BackofficeAdStatsResponse(message="광고 통계 조회 성공", data=await ads.get_stats(db=db, ad=ad, query=query))
