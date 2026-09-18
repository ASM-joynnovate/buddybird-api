from datetime import date, datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field

from app.enums import NotificationKindEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class NotificationImageDTO(CustomBaseModel):
    url: str


class NotificationDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"image", "sound_id", "emergency_event_id", "report_date", "read_at"}

    id: UUID
    kind: NotificationKindEnum
    title: str
    body: str
    image: NotificationImageDTO | None
    sound_id: UUID | None
    emergency_event_id: UUID | None
    report_date: date | None
    sent_at: datetime
    read_at: datetime | None


class NotificationResponse(BaseResponse):
    data: NotificationDTO


class NotificationListResponse(BaseResponse):
    data: list[NotificationDTO]


class NotificationSendResponse(BaseResponse):
    data: NotificationDTO | None


class SendNotificationRequest(BaseRequest):
    user_id: UUID
    kind: NotificationKindEnum
    title: str = Field(..., min_length=1, max_length=100)
    body: str = Field(..., min_length=1, max_length=500)
