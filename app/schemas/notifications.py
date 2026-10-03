from datetime import date, datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field

from app.enums import NotificationKindEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class NotificationImageDTO(CustomBaseModel):
    url: str


class MimicryNotificationDataDTO(CustomBaseModel):
    sound_id: UUID
    session_id: UUID


class DailySummaryNotificationDataDTO(CustomBaseModel):
    report_date: date


class NotificationDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"image", "data", "read_at"}

    id: UUID
    kind: NotificationKindEnum
    title: str
    body: str
    image: NotificationImageDTO | None
    data: MimicryNotificationDataDTO | DailySummaryNotificationDataDTO | None
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
