from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.db import get_or_404
from app.dependencies import DBSession, Storage
from app.models import User
from app.schemas.base import UploadRequest, UploadResponse
from app.schemas.notifications import (
    BackofficeNotificationAudienceParams,
    BackofficeNotificationAudienceResponse,
    BackofficeNotificationDispatchCancelResponse,
    BackofficeNotificationDispatchDetailResponse,
    BackofficeNotificationDispatchListParams,
    BackofficeNotificationDispatchListResponse,
    BackofficeNotificationListParams,
    BackofficeNotificationListResponse,
    BackofficeNotificationResponse,
    BackofficePushDeliveryListParams,
    BackofficePushDeliveryListResponse,
    BroadcastNotificationRequest,
    BroadcastNotificationResponse,
    SendNotificationRequest,
)
from app.services import notifications

router = APIRouter(prefix="/notifications")


@router.get("", name="알림 발송 이력 조회")
async def get_list(
    query: Annotated[BackofficeNotificationListParams, Query()], db: DBSession, storage: Storage
) -> BackofficeNotificationListResponse:
    items, total = await notifications.get_backoffice_list(db=db, storage=storage, query=query)

    return BackofficeNotificationListResponse(
        message="알림 발송 이력 조회 성공",
        data=items,
        meta={**query.meta(total), "total_count": total},
    )


@router.get("/dispatches", name="발송 목록 조회")
async def get_dispatches(
    query: Annotated[BackofficeNotificationDispatchListParams, Query()], db: DBSession, storage: Storage
) -> BackofficeNotificationDispatchListResponse:
    items, total = await notifications.get_backoffice_dispatches(db=db, storage=storage, query=query)

    return BackofficeNotificationDispatchListResponse(
        message="발송 목록 조회 성공",
        data=items,
        meta={**query.meta(total), "total_count": total},
    )


@router.get("/dispatches/{dispatch_id}", name="발송 상세 조회")
async def get_dispatch(
    dispatch_id: UUID, db: DBSession, storage: Storage
) -> BackofficeNotificationDispatchDetailResponse:
    return BackofficeNotificationDispatchDetailResponse(
        message="발송 상세 조회 성공",
        data=await notifications.get_backoffice_dispatch(db=db, storage=storage, dispatch_id=dispatch_id),
    )


@router.get("/audience", name="받는 사람 수 조회")
async def get_audience(
    query: Annotated[BackofficeNotificationAudienceParams, Query()], db: DBSession
) -> BackofficeNotificationAudienceResponse:
    return BackofficeNotificationAudienceResponse(
        message="받는 사람 수 조회 성공",
        data=await notifications.get_backoffice_audience(db=db, query=query),
    )


@router.get("/deliveries", name="푸시 발송 기록 조회")
async def get_deliveries(
    query: Annotated[BackofficePushDeliveryListParams, Query()], db: DBSession
) -> BackofficePushDeliveryListResponse:
    items, total = await notifications.get_backoffice_deliveries(db=db, query=query)

    return BackofficePushDeliveryListResponse(
        message="푸시 발송 기록 조회 성공",
        data=items,
        meta=query.meta(total),
    )


@router.post("", name="알림 발송")
async def send(body: SendNotificationRequest, db: DBSession, storage: Storage) -> BackofficeNotificationResponse:
    user = await get_or_404(db=db, model=User, id=body.user_id)
    dto = await notifications.send(db=db, storage=storage, user=user, data=body)

    if dto is None:
        return BackofficeNotificationResponse(message="알림 설정이 꺼져 있어 발송하지 않음", data=None)

    return BackofficeNotificationResponse(message="알림 발송 성공", data=dto)


@router.post("/broadcast", name="알림 일괄 발송")
async def broadcast(body: BroadcastNotificationRequest, db: DBSession) -> BroadcastNotificationResponse:
    return BroadcastNotificationResponse(
        message="알림 일괄 발송 성공", data=await notifications.broadcast(db=db, data=body)
    )


@router.post("/dispatches/{dispatch_id}/cancel", name="발송 예약 취소")
async def cancel_dispatch(dispatch_id: UUID, db: DBSession) -> BackofficeNotificationDispatchCancelResponse:
    return BackofficeNotificationDispatchCancelResponse(
        message="발송 예약 취소 성공",
        data=await notifications.cancel_dispatch(db=db, dispatch_id=dispatch_id),
    )


@router.post("/images", name="알림 사진 업로드 URL 발급")
async def add_image(body: UploadRequest, db: DBSession, storage: Storage) -> UploadResponse:
    return UploadResponse(
        message="알림 사진 업로드 URL 발급 성공",
        data=await notifications.add_image(db=db, storage=storage, data=body),
    )
