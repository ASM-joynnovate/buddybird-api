from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import ActiveUser, DBSession, Locale, Storage, require_notification
from app.models import Notification
from app.schemas.base import BaseResponse, PageParams
from app.schemas.notifications import NotificationListResponse, NotificationResponse
from app.services import notifications

router = APIRouter(prefix="/notifications")


@router.get("", name="알림 목록 조회")
async def get_list(
    user: ActiveUser, locale: Locale, query: Annotated[PageParams, Query()], db: DBSession, storage: Storage
) -> NotificationListResponse:
    items, total = await notifications.get_list(db=db, storage=storage, user=user, locale=locale, query=query)

    return NotificationListResponse(
        message="알림 목록 조회 성공",
        data=items,
        meta=query.meta(total),
    )


@router.get("/{notification_id}", name="알림 상세 조회")
async def get_detail(
    notification: Annotated[Notification, Depends(require_notification)], locale: Locale, storage: Storage
) -> NotificationResponse:
    return NotificationResponse(
        message="알림 상세 조회 성공",
        data=notifications.build_notification_dto(notification, locale, storage),
    )


@router.post("/read-all", name="알림 전체 읽음 처리")
async def mark_all_read(user: ActiveUser, db: DBSession) -> BaseResponse:
    await notifications.mark_all_read(db=db, user=user)

    return BaseResponse(message="알림 전체 읽음 처리 성공")


@router.post("/{notification_id}/read", name="알림 읽음 처리")
async def mark_read(
    notification: Annotated[Notification, Depends(require_notification)],
    locale: Locale,
    db: DBSession,
    storage: Storage,
) -> NotificationResponse:
    return NotificationResponse(
        message="알림 읽음 처리 성공",
        data=await notifications.mark_read(db=db, storage=storage, notification=notification, locale=locale),
    )
