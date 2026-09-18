from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.db import get_or_404
from app.dependencies import ActiveUser, DBSession, Storage, require_backoffice, require_notification
from app.models import Notification, User
from app.schemas.base import BaseResponse, PageParams
from app.schemas.notifications import (
    NotificationListResponse,
    NotificationResponse,
    NotificationSendResponse,
    SendNotificationRequest,
)
from app.services import notifications

router = APIRouter(prefix="/notifications")


@router.get("", name="알림 목록 조회", response_model=NotificationListResponse)
async def get_list(
    user: ActiveUser, query: Annotated[PageParams, Query()], db: DBSession, storage: Storage
) -> NotificationListResponse:
    items, total = await notifications.get_list(db=db, storage=storage, user=user, query=query)

    return NotificationListResponse(
        message="알림 목록 조회 성공",
        data=items,
        meta={
            "current_page": query.page,
            "total_page_count": (total + query.count_by_page - 1) // query.count_by_page,
            "is_first": query.page == 1,
            "is_last": query.page * query.count_by_page >= total,
        },
    )


@router.post("/read-all", name="알림 전체 읽음 처리")
async def mark_all_read(user: ActiveUser, db: DBSession) -> BaseResponse:
    await notifications.mark_all_read(db=db, user=user)

    return BaseResponse(message="알림 전체 읽음 처리 성공")


@router.post("/{notification_id}/read", name="알림 읽음 처리", response_model=NotificationResponse)
async def mark_read(
    notification: Annotated[Notification, Depends(require_notification)], db: DBSession, storage: Storage
) -> NotificationResponse:
    return NotificationResponse(
        message="알림 읽음 처리 성공",
        data=await notifications.mark_read(db=db, storage=storage, notification=notification),
    )


@router.post("", name="알림 발송", response_model=NotificationSendResponse, dependencies=[Depends(require_backoffice)])
async def send(body: SendNotificationRequest, db: DBSession, storage: Storage) -> NotificationSendResponse:
    user = await get_or_404(db=db, model=User, id=body.user_id)
    dto = await notifications.send(db=db, storage=storage, user=user, kind=body.kind, title=body.title, body=body.body)

    if dto is None:
        return NotificationSendResponse(message="알림 설정이 꺼져 있어 발송하지 않음", data=None)

    return NotificationSendResponse(message="알림 발송 성공", data=dto)
