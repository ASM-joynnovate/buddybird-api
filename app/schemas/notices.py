from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import AwareDatetime, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.schemas.base import (
    BaseRequest,
    BaseResponse,
    CustomBaseModel,
    I18nBodyRequest,
    I18nDTO,
    I18nTitleRequest,
    UpdateI18nBodyRequest,
    UpdateI18nTitleRequest,
)


class NoticeImageDTO(CustomBaseModel):
    id: UUID
    url: str


class NoticeDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"body", "ends_at"}

    id: UUID
    title: str
    body: str | None
    starts_at: datetime
    ends_at: datetime | None
    is_read: bool
    images: list[NoticeImageDTO]


class NoticeResponse(BaseResponse):
    data: NoticeDTO


class NoticeListResponse(BaseResponse):
    data: list[NoticeDTO]


class BackofficeNoticeDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"body", "ends_at"}

    id: UUID
    title: I18nDTO
    body: I18nDTO | None
    starts_at: datetime
    ends_at: datetime | None
    images: list[NoticeImageDTO]


class BackofficeNoticeResponse(BaseResponse):
    data: BackofficeNoticeDTO


class CreateNoticeRequest(BaseRequest):
    null_fields: ClassVar[set] = {"body", "ends_at"}

    title: I18nTitleRequest
    body: I18nBodyRequest | None = None
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_period(self) -> CreateNoticeRequest:
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("게시 종료 시각은 게시 시작 시각보다 늦어야 합니다.")

        return self


class UpdateNoticeRequest(BaseRequest):
    null_fields: ClassVar[set] = {"body", "ends_at"}

    title: UpdateI18nTitleRequest | MISSING = MISSING
    body: UpdateI18nBodyRequest | MISSING | None = MISSING
    starts_at: AwareDatetime | MISSING = MISSING
    ends_at: AwareDatetime | MISSING | None = MISSING
