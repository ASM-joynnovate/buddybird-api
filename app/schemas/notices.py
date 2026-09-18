from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import AwareDatetime, field_validator, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


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


class CreateNoticeRequest(BaseRequest):
    null_fields: ClassVar[set] = {"body", "ends_at"}

    title: str
    body: str | None = None
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()

        if not 1 <= len(value) <= 100:
            raise ValueError("제목은 1~100자여야 합니다.")

        return value

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str | None) -> str | None:
        if value is None:
            return value

        value = value.strip()

        if len(value) == 0:
            raise ValueError("본문을 입력해 주세요.")

        return value

    @model_validator(mode="after")
    def validate_period(self) -> CreateNoticeRequest:
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("게시 종료 시각은 게시 시작 시각보다 늦어야 합니다.")

        return self


class UpdateNoticeRequest(BaseRequest):
    null_fields: ClassVar[set] = {"body", "ends_at"}

    title: str | MISSING = MISSING
    body: str | MISSING | None = MISSING
    starts_at: AwareDatetime | MISSING = MISSING
    ends_at: AwareDatetime | MISSING | None = MISSING

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | MISSING) -> str | MISSING:
        if not isinstance(value, str):
            return value

        value = value.strip()

        if not 1 <= len(value) <= 100:
            raise ValueError("제목은 1~100자여야 합니다.")

        return value

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str | MISSING | None) -> str | MISSING | None:
        if not isinstance(value, str):
            return value

        value = value.strip()

        if len(value) == 0:
            raise ValueError("본문을 입력해 주세요.")

        return value
