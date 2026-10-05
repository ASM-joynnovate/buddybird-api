from datetime import datetime, time
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.enums import NotificationKindEnum
from app.schemas.base import BaseRequest, BaseResponse, Body, CustomBaseModel, I18nDTO, I18nTitleRequest, PageParams


class NotificationImageDTO(CustomBaseModel):
    url: str


class NotificationDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"image", "data_id", "read_at"}

    id: UUID
    kind: NotificationKindEnum
    title: str
    body: str
    image: NotificationImageDTO | None
    data_id: UUID | None
    sent_at: datetime
    read_at: datetime | None


class NotificationResponse(BaseResponse):
    data: NotificationDTO


class NotificationListResponse(BaseResponse):
    data: list[NotificationDTO]


class BackofficeNotificationDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"image", "data_id", "read_at"}

    id: UUID
    user_id: UUID
    kind: NotificationKindEnum
    data_id: UUID | None
    title: I18nDTO
    body: I18nDTO
    image: NotificationImageDTO | None
    sent_at: datetime
    read_at: datetime | None


class NotificationSendResponse(BaseResponse):
    data: BackofficeNotificationDTO | None


class BackofficeNotificationListResponse(BaseResponse):
    data: list[BackofficeNotificationDTO]


class BroadcastNotificationDTO(CustomBaseModel):
    notification_count: int


class BroadcastNotificationResponse(BaseResponse):
    data: BroadcastNotificationDTO


class I18nNotificationBodyRequest(BaseRequest):
    null_fields: ClassVar[set] = {"ko_kr"}

    ko_kr: Body | None = Field(None, max_length=500)
    en_us: Body = Field(..., max_length=500)


class NotificationContentRequest(BaseRequest):
    null_fields: ClassVar[set] = {"image_file_id"}

    kind: Literal[NotificationKindEnum.ANNOUNCEMENT, NotificationKindEnum.URGENT, NotificationKindEnum.MARKETING]
    title: I18nTitleRequest
    body: I18nNotificationBodyRequest
    image_file_id: UUID | None = None


class SendNotificationRequest(NotificationContentRequest):
    user_id: UUID


class BroadcastNotificationRequest(NotificationContentRequest):
    null_fields: ClassVar[set] = {"image_file_id", "push_local_time"}

    user_ids: list[UUID] | None = Field(None, min_length=1, max_length=1000)
    all_users: bool = False
    push_local_time: time | None = None

    @model_validator(mode="after")
    def validate_broadcast(self) -> BroadcastNotificationRequest:
        if (self.user_ids is not None) == self.all_users:
            raise ValueError("user_ids와 all_users 중 하나만 지정해야 합니다.")

        if self.kind == NotificationKindEnum.URGENT and self.push_local_time is not None:
            raise ValueError("urgent에는 push_local_time을 지정할 수 없습니다.")

        return self


class BackofficeNotificationListParams(PageParams):
    user_id: UUID | None = None
    kind: NotificationKindEnum | None = None
