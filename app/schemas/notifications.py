from datetime import date, datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import Field, NaiveDatetime, model_validator

from app.enums import NotificationDispatchStatusEnum, NotificationDispatchTargetEnum, NotificationKindEnum
from app.schemas.base import (
    BaseRequest,
    BaseResponse,
    Body,
    CustomBaseModel,
    FileDTO,
    I18nDTO,
    I18nTitleRequest,
    PageParams,
)


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


class BackofficeNotificationUserDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"nickname", "email", "photo_file"}

    nickname: str | None
    email: str | None
    is_anonymous: bool
    photo_file: FileDTO | None


class BackofficeNotificationListItemDTO(BackofficeNotificationDTO):
    allow_null_fields: ClassVar[set] = {"image", "data_id", "read_at", "push_sent_at"}

    user: BackofficeNotificationUserDTO
    push_sent_at: datetime | None


class BackofficeNotificationListResponse(BaseResponse):
    data: list[BackofficeNotificationListItemDTO]


class BackofficeNotificationDispatchSendTimeDTO(CustomBaseModel):
    sent_at: datetime
    count: int


class BackofficeNotificationDispatchRecipientDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"nickname", "email", "photo_file", "read_at", "push_sent_at"}

    user_id: UUID
    nickname: str | None
    email: str | None
    is_anonymous: bool
    photo_file: FileDTO | None
    read_at: datetime | None
    push_sent_at: datetime | None


class BackofficeNotificationDispatchDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"image", "image_file_id", "recipient_local_datetime", "recipient"}

    id: UUID
    kind: NotificationKindEnum
    title: I18nDTO
    body: I18nDTO
    image: NotificationImageDTO | None
    image_file_id: UUID | None
    target: NotificationDispatchTargetEnum
    recipient_local_datetime: NaiveDatetime | None
    created_at: datetime
    status: NotificationDispatchStatusEnum
    recipient_count: int
    sent_count: int
    read_count: int
    push_sent_count: int
    push_waiting_count: int
    send_times: list[BackofficeNotificationDispatchSendTimeDTO]
    recipient: BackofficeNotificationDispatchRecipientDTO | None


class BackofficeNotificationDispatchListResponse(BaseResponse):
    data: list[BackofficeNotificationDispatchDTO]


class BackofficeNotificationDispatchHourlyReadDTO(CustomBaseModel):
    hour: int
    count: int


class BackofficeNotificationDispatchDetailDTO(BackofficeNotificationDispatchDTO):
    hourly_reads: list[BackofficeNotificationDispatchHourlyReadDTO]


class BackofficeNotificationDispatchDetailResponse(BaseResponse):
    data: BackofficeNotificationDispatchDetailDTO


class BackofficeNotificationDispatchCancelDTO(CustomBaseModel):
    canceled_count: int


class BackofficeNotificationDispatchCancelResponse(BaseResponse):
    data: BackofficeNotificationDispatchCancelDTO


class BackofficeNotificationAudienceDTO(CustomBaseModel):
    user_count: int
    recipient_count: int
    pushable_count: int


class BackofficeNotificationAudienceResponse(BaseResponse):
    data: BackofficeNotificationAudienceDTO


class BackofficePushDeliveryDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"notification_id", "announcement_id", "body"}

    id: UUID
    notification_id: UUID | None
    announcement_id: UUID | None
    kind: NotificationKindEnum
    title: I18nDTO
    body: I18nDTO | None
    scheduled_at: datetime
    sent_at: datetime


class BackofficePushDeliveryListResponse(BaseResponse):
    data: list[BackofficePushDeliveryDTO]


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
    null_fields: ClassVar[set] = {"image_file_id", "recipient_local_datetime"}

    user_ids: list[UUID] | None = Field(None, min_length=1, max_length=1000)
    all_users: bool = False
    recipient_local_datetime: NaiveDatetime | None = None

    @model_validator(mode="after")
    def validate_broadcast(self) -> BroadcastNotificationRequest:
        if (self.user_ids is not None) == self.all_users:
            raise ValueError("user_ids와 all_users 중 하나만 지정해야 합니다.")

        if self.kind == NotificationKindEnum.URGENT and self.recipient_local_datetime is not None:
            raise ValueError("urgent에는 recipient_local_datetime을 지정할 수 없습니다.")

        return self


class BackofficeNotificationListParams(PageParams):
    user_id: UUID | None = None
    kind: NotificationKindEnum | None = None
    is_sent: bool | None = None
    keyword: str | None = Field(None, min_length=1, max_length=100)
    sent_from: date | None = None
    sent_to: date | None = None


class BackofficeNotificationDispatchListParams(PageParams):
    is_sent: bool | None = None
    kind: (
        Literal[NotificationKindEnum.ANNOUNCEMENT, NotificationKindEnum.URGENT, NotificationKindEnum.MARKETING] | None
    ) = None
    keyword: str | None = Field(None, min_length=1, max_length=100)
    sent_from: date | None = None
    sent_to: date | None = None


class BackofficeNotificationAudienceParams(BaseRequest):
    kind: Literal[NotificationKindEnum.ANNOUNCEMENT, NotificationKindEnum.URGENT, NotificationKindEnum.MARKETING]


class BackofficePushDeliveryListParams(PageParams):
    device_id: UUID
