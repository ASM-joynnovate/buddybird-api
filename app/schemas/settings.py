from datetime import time

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class SleepSettingsDTO(CustomBaseModel):
    sleep_at: time
    wake_at: time


class NotificationSettingsDTO(CustomBaseModel):
    push_enabled: bool
    announcement_enabled: bool
    report_enabled: bool
    marketing_enabled: bool
    marketing_night_enabled: bool


class SettingsDTO(CustomBaseModel):
    sleep: SleepSettingsDTO
    notifications: NotificationSettingsDTO


class SettingsResponse(BaseResponse):
    data: SettingsDTO


class UpdateSleepSettingsRequest(BaseRequest):
    sleep_at: time
    wake_at: time


class UpdateNotificationSettingsRequest(BaseRequest):
    push_enabled: bool
    announcement_enabled: bool
    report_enabled: bool
    marketing_enabled: bool
    marketing_night_enabled: bool
