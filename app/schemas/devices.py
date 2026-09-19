from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field, field_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.enums import DeviceRoleEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class DeviceClientDTO(CustomBaseModel):
    platform: str
    os_version: str
    model: str
    app_version: str


class DeviceDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"timezone", "last_seen_at"}

    id: UUID
    client_device_id: UUID
    role: DeviceRoleEnum
    timezone: str | None
    last_seen_at: datetime | None
    client: DeviceClientDTO
    push_registered: bool


class DeviceResponse(BaseResponse):
    data: DeviceDTO


class DeviceListResponse(BaseResponse):
    data: list[DeviceDTO]


class RegisterDeviceRequest(BaseRequest):
    null_fields: ClassVar[set] = {"timezone"}

    client_device_id: UUID
    role: DeviceRoleEnum
    platform: str = Field(..., min_length=1, max_length=10)
    os_version: str = Field(..., min_length=1, max_length=20)
    model: str = Field(..., min_length=1, max_length=30)
    app_version: str = Field(..., min_length=1, max_length=12)
    timezone: str | None = Field(None, min_length=1, max_length=64)


class UpdatePushTokenRequest(BaseRequest):
    token: str = Field(..., min_length=1, max_length=4096)


class UpdateDeviceRequest(BaseRequest):
    null_fields: ClassVar[set] = {"timezone"}

    app_version: str | MISSING = MISSING
    os_version: str | MISSING = MISSING
    timezone: str | MISSING | None = MISSING

    @field_validator("app_version")
    @classmethod
    def validate_app_version(cls, value: str | MISSING) -> str | MISSING:
        if isinstance(value, str) and not 1 <= len(value) <= 12:
            raise ValueError("앱 버전은 1~12자여야 합니다.")

        return value

    @field_validator("os_version")
    @classmethod
    def validate_os_version(cls, value: str | MISSING) -> str | MISSING:
        if isinstance(value, str) and not 1 <= len(value) <= 20:
            raise ValueError("OS 버전은 1~20자여야 합니다.")

        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | MISSING | None) -> str | MISSING | None:
        if isinstance(value, str) and not 1 <= len(value) <= 64:
            raise ValueError("시간대는 1~64자여야 합니다.")

        return value
