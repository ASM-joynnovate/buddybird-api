from typing import Annotated

from fastapi import APIRouter, Query

from app.db import get_or_404
from app.dependencies import DBSession, Storage
from app.models import User
from app.schemas.base import UploadRequest, UploadResponse
from app.schemas.notifications import (
    BackofficeNotificationListParams,
    BackofficeNotificationListResponse,
    BroadcastNotificationRequest,
    BroadcastNotificationResponse,
    NotificationSendResponse,
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
        meta=query.meta(total),
    )


@router.post("", name="알림 발송")
async def send(body: SendNotificationRequest, db: DBSession, storage: Storage) -> NotificationSendResponse:
    user = await get_or_404(db=db, model=User, id=body.user_id)
    dto = await notifications.send(db=db, storage=storage, user=user, data=body)

    if dto is None:
        return NotificationSendResponse(message="알림 설정이 꺼져 있어 발송하지 않음", data=None)

    return NotificationSendResponse(message="알림 발송 성공", data=dto)


@router.post("/broadcast", name="알림 일괄 발송")
async def broadcast(body: BroadcastNotificationRequest, db: DBSession) -> BroadcastNotificationResponse:
    return BroadcastNotificationResponse(
        message="알림 일괄 발송 성공", data=await notifications.broadcast(db=db, data=body)
    )


@router.post("/images", name="알림 사진 업로드 URL 발급")
async def add_image(body: UploadRequest, db: DBSession, storage: Storage) -> UploadResponse:
    return UploadResponse(
        message="알림 사진 업로드 URL 발급 성공",
        data=await notifications.add_image(db=db, storage=storage, data=body),
    )
