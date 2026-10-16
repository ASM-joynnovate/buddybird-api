from datetime import datetime, time
from typing import ClassVar
from uuid import UUID

from pydantic import Field
from pydantic.experimental.missing_sentinel import MISSING

from app.enums import NotificationSettingKindEnum
from app.schemas.base import (
    BaseRequest,
    BaseResponse,
    CustomBaseModel,
    I18nBodyRequest,
    I18nDTO,
    I18nTitleRequest,
    UpdateI18nTitleRequest,
)


class SleepSettingsDTO(CustomBaseModel):
    sleep_at: time
    wake_at: time


class NotificationSettingsDTO(CustomBaseModel):
    push_enabled: bool
    announcement_enabled: bool
    report_enabled: bool
    emergency_enabled: bool
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
    emergency_enabled: bool | MISSING = MISSING
    marketing_enabled: bool
    marketing_night_enabled: bool


class NotificationSettingItemDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"description"}

    id: UUID
    kind: str
    title: str
    description: str | None
    enabled: bool


class NotificationSettingGroupDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"description"}

    id: UUID
    title: str
    description: str | None
    items: list[NotificationSettingItemDTO]


class NotificationSettingListDTO(CustomBaseModel):
    push_enabled: bool
    groups: list[NotificationSettingGroupDTO]
    items: list[NotificationSettingItemDTO]


class NotificationSettingListResponse(BaseResponse):
    data: NotificationSettingListDTO


class UpdatePushSettingRequest(BaseRequest):
    push_enabled: bool


class SaveUserNotificationSettingRequest(BaseRequest):
    enabled: bool


class BackofficeNotificationSettingGroupDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"description"}

    id: UUID
    title: I18nDTO
    description: I18nDTO | None
    sort_order: int


class BackofficeNotificationSettingGroupResponse(BaseResponse):
    data: BackofficeNotificationSettingGroupDTO


class BackofficeNotificationSettingGroupListResponse(BaseResponse):
    data: list[BackofficeNotificationSettingGroupDTO]


class BackofficeNotificationSettingItemDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"group_id", "description"}

    id: UUID
    group_id: UUID | None
    kind: str
    title: I18nDTO
    description: I18nDTO | None
    default_enabled: bool
    sort_order: int


class BackofficeNotificationSettingItemResponse(BaseResponse):
    data: BackofficeNotificationSettingItemDTO


class BackofficeNotificationSettingItemListResponse(BaseResponse):
    data: list[BackofficeNotificationSettingItemDTO]


class BackofficeUserNotificationSettingItemDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"description", "decided_at"}

    id: UUID
    kind: str
    title: I18nDTO
    description: I18nDTO | None
    enabled: bool
    decided_at: datetime | None


class BackofficeUserNotificationSettingGroupDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"description"}

    id: UUID
    title: I18nDTO
    description: I18nDTO | None
    items: list[BackofficeUserNotificationSettingItemDTO]


class BackofficeUserNotificationSettingListDTO(CustomBaseModel):
    push_enabled: bool
    groups: list[BackofficeUserNotificationSettingGroupDTO]
    items: list[BackofficeUserNotificationSettingItemDTO]


class BackofficeUserNotificationSettingListResponse(BaseResponse):
    data: BackofficeUserNotificationSettingListDTO


class CreateNotificationSettingGroupRequest(BaseRequest):
    null_fields: ClassVar[set] = {"description"}

    title: I18nTitleRequest
    description: I18nBodyRequest | None = None
    sort_order: int = Field(ge=0, le=32767)


class UpdateNotificationSettingGroupRequest(BaseRequest):
    null_fields: ClassVar[set] = {"description"}

    title: UpdateI18nTitleRequest | MISSING = MISSING
    description: I18nBodyRequest | MISSING | None = MISSING
    sort_order: int | MISSING = Field(MISSING, ge=0, le=32767)


class CreateNotificationSettingItemRequest(BaseRequest):
    null_fields: ClassVar[set] = {"group_id", "description"}

    group_id: UUID | None = None
    kind: NotificationSettingKindEnum
    title: I18nTitleRequest
    description: I18nBodyRequest | None = None
    default_enabled: bool
    sort_order: int = Field(ge=0, le=32767)


class UpdateNotificationSettingItemRequest(BaseRequest):
    null_fields: ClassVar[set] = {"group_id", "description"}

    group_id: UUID | MISSING | None = MISSING
    title: UpdateI18nTitleRequest | MISSING = MISSING
    description: I18nBodyRequest | MISSING | None = MISSING
    sort_order: int | MISSING = Field(MISSING, ge=0, le=32767)
