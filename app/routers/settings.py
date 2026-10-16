from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import ActiveUser, DBSession, Locale, require_notification_setting_item
from app.models import NotificationSettingItem
from app.schemas.settings import (
    NotificationSettingListResponse,
    SaveUserNotificationSettingRequest,
    SettingsResponse,
    UpdateNotificationSettingsRequest,
    UpdatePushSettingRequest,
    UpdateSleepSettingsRequest,
)
from app.services import settings

router = APIRouter(prefix="/users/me/settings")


@router.get("", name="설정 조회")
async def get_settings(user: ActiveUser, db: DBSession) -> SettingsResponse:
    return SettingsResponse(message="설정 조회 성공", data=await settings.get_settings(db=db, user=user))


@router.put("/sleep", name="수면 시간 수정")
async def update_sleep(user: ActiveUser, body: UpdateSleepSettingsRequest, db: DBSession) -> SettingsResponse:
    return SettingsResponse(
        message="수면 시간 수정 성공", data=await settings.update_sleep(db=db, user=user, data=body)
    )


@router.put("/notifications", name="알림 설정 수정")
async def update_notifications(
    user: ActiveUser, body: UpdateNotificationSettingsRequest, db: DBSession
) -> SettingsResponse:
    return SettingsResponse(
        message="알림 설정 수정 성공", data=await settings.update_notifications(db=db, user=user, data=body)
    )


@router.get("/notifications", name="알림 설정 목록 조회")
async def get_notification_settings(user: ActiveUser, locale: Locale, db: DBSession) -> NotificationSettingListResponse:
    return NotificationSettingListResponse(
        message="알림 설정 목록 조회 성공",
        data=await settings.get_notification_settings(db=db, user=user, locale=locale),
    )


@router.patch("/notifications", name="푸시 알림 설정 수정")
async def update_push(
    user: ActiveUser, body: UpdatePushSettingRequest, locale: Locale, db: DBSession
) -> NotificationSettingListResponse:
    return NotificationSettingListResponse(
        message="푸시 알림 설정 수정 성공",
        data=await settings.update_push(db=db, user=user, data=body, locale=locale),
    )


@router.patch("/notifications/{item_id}", name="알림 설정 항목 수정")
async def save_notification_setting(
    user: ActiveUser,
    item: Annotated[NotificationSettingItem, Depends(require_notification_setting_item)],
    body: SaveUserNotificationSettingRequest,
    locale: Locale,
    db: DBSession,
) -> NotificationSettingListResponse:
    return NotificationSettingListResponse(
        message="알림 설정 항목 수정 성공",
        data=await settings.save_notification_setting(db=db, user=user, item=item, data=body, locale=locale),
    )
