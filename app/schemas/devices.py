from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field
from pydantic.experimental.missing_sentinel import MISSING

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
    platform: str = Field(..., min_length=1, max_length=10)
    os_version: str = Field(..., min_length=1, max_length=20)
    model: str = Field(..., min_length=1, max_length=30)
    app_version: str = Field(..., min_length=1, max_length=12)
    timezone: str | None = Field(None, min_length=1, max_length=64)


class UpdatePushTokenRequest(BaseRequest):
    token: str = Field(..., min_length=1, max_length=4096)


class UpdateDeviceRequest(BaseRequest):
    null_fields: ClassVar[set] = {"timezone"}

    app_version: str | MISSING = Field(MISSING, min_length=1, max_length=12)
    os_version: str | MISSING = Field(MISSING, min_length=1, max_length=20)
    timezone: str | MISSING | None = Field(MISSING, min_length=1, max_length=64)
