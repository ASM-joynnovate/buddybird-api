from datetime import date, datetime
from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import Field, StringConstraints

from app.enums import LocaleEnum, PlatformEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, FileDTO, PageParams


class FeedbackDTO(CustomBaseModel):
    id: UUID
    user_id: UUID
    device_id: UUID
    message: str
    app_version: str
    created_at: datetime


class FeedbackResponse(BaseResponse):
    data: FeedbackDTO


class BackofficeFeedbackUserDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"nickname", "email", "photo_file"}

    nickname: str | None
    email: str | None
    is_anonymous: bool
    is_deleted: bool
    photo_file: FileDTO | None


class BackofficeFeedbackDeviceDTO(CustomBaseModel):
    platform: str
    os_version: str
    model: str
    locale: str


class BackofficeFeedbackDTO(FeedbackDTO):
    is_unsupported: bool
    user: BackofficeFeedbackUserDTO
    device: BackofficeFeedbackDeviceDTO


class BackofficeFeedbackListResponse(BaseResponse):
    data: list[BackofficeFeedbackDTO]


class CreateFeedbackRequest(BaseRequest):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class BackofficeFeedbackListParams(PageParams):
    user_id: UUID | None = None
    keyword: str | None = Field(None, min_length=1, max_length=100)
    created_from: date | None = None
    created_to: date | None = None
    app_version: str | None = None
    platform: PlatformEnum | None = None
    locale: LocaleEnum | None = None
