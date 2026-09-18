from datetime import time

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class SleepSettingsDTO(CustomBaseModel):
    sleep_at: time
    wake_at: time


class NotificationSettingsDTO(CustomBaseModel):
    emergency: bool
    mimicry: bool
    daily_summary: bool
    streak: bool
    station_disconnect: bool


class SettingsDTO(CustomBaseModel):
    sleep: SleepSettingsDTO
    notifications: NotificationSettingsDTO


class SettingsResponse(BaseResponse):
    data: SettingsDTO


class UpdateSleepSettingsRequest(BaseRequest):
    sleep_at: time
    wake_at: time


class UpdateNotificationSettingsRequest(BaseRequest):
    emergency: bool
    mimicry: bool
    daily_summary: bool
    streak: bool
    station_disconnect: bool
