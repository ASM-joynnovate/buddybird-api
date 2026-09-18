from fastapi import APIRouter

from app.dependencies import ActiveUser, DBSession
from app.schemas.settings import SettingsResponse, UpdateNotificationSettingsRequest, UpdateSleepSettingsRequest
from app.services import settings

router = APIRouter(prefix="/users/me/settings")


@router.get("", name="설정 조회", response_model=SettingsResponse)
async def get_settings(user: ActiveUser, db: DBSession) -> SettingsResponse:
    return SettingsResponse(message="설정 조회 성공", data=await settings.get_settings(db=db, user=user))


@router.put("/sleep", name="수면 시간 수정", response_model=SettingsResponse)
async def update_sleep(user: ActiveUser, body: UpdateSleepSettingsRequest, db: DBSession) -> SettingsResponse:
    return SettingsResponse(
        message="수면 시간 수정 성공", data=await settings.update_sleep(db=db, user=user, data=body)
    )


@router.put("/notifications", name="알림 설정 수정", response_model=SettingsResponse)
async def update_notifications(
    user: ActiveUser, body: UpdateNotificationSettingsRequest, db: DBSession
) -> SettingsResponse:
    return SettingsResponse(
        message="알림 설정 수정 성공", data=await settings.update_notifications(db=db, user=user, data=body)
    )
