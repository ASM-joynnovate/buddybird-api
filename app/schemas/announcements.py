from datetime import datetime, time
from typing import ClassVar
from uuid import UUID

from pydantic import AwareDatetime, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.enums import AnnouncementSortEnum, SortOrderEnum
from app.schemas.base import (
    BaseRequest,
    BaseResponse,
    CustomBaseModel,
    I18nBodyRequest,
    I18nDTO,
    I18nTitleRequest,
    PageParams,
    UpdateI18nBodyRequest,
    UpdateI18nTitleRequest,
)


class AnnouncementImageDTO(CustomBaseModel):
    id: UUID
    url: str


class AnnouncementDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"body", "ends_at"}

    id: UUID
    title: str
    body: str | None
    starts_at: datetime
    ends_at: datetime | None
    is_read: bool
    images: list[AnnouncementImageDTO]


class AnnouncementResponse(BaseResponse):
    data: AnnouncementDTO


class AnnouncementListResponse(BaseResponse):
    data: list[AnnouncementDTO]


class BackofficeAnnouncementDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"body", "ends_at", "push_local_time", "push_prepared_at"}

    id: UUID
    title: I18nDTO
    body: I18nDTO | None
    starts_at: datetime
    ends_at: datetime | None
    push_enabled: bool
    push_local_time: time | None
    push_prepared_at: datetime | None
    images: list[AnnouncementImageDTO]


class BackofficeAnnouncementResponse(BaseResponse):
    data: BackofficeAnnouncementDTO


class BackofficeAnnouncementListItemDTO(BackofficeAnnouncementDTO):
    read_count: int


class BackofficeAnnouncementListResponse(BaseResponse):
    data: list[BackofficeAnnouncementListItemDTO]


class CreateAnnouncementRequest(BaseRequest):
    null_fields: ClassVar[set] = {"body", "ends_at", "push_local_time"}

    title: I18nTitleRequest
    body: I18nBodyRequest | None = None
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None
    push_enabled: bool = False
    push_local_time: time | None = None

    @model_validator(mode="after")
    def validate_period(self) -> CreateAnnouncementRequest:
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("게시 종료 시각은 게시 시작 시각보다 늦어야 합니다.")

        return self


class UpdateAnnouncementRequest(BaseRequest):
    null_fields: ClassVar[set] = {"body", "ends_at", "push_local_time"}

    title: UpdateI18nTitleRequest | MISSING = MISSING
    body: UpdateI18nBodyRequest | MISSING | None = MISSING
    starts_at: AwareDatetime | MISSING = MISSING
    ends_at: AwareDatetime | MISSING | None = MISSING
    push_enabled: bool | MISSING = MISSING
    push_local_time: time | MISSING | None = MISSING


class BackofficeAnnouncementListParams(PageParams):
    is_ended: bool | None = None
    sort: AnnouncementSortEnum = AnnouncementSortEnum.STARTS_AT
    order: SortOrderEnum = SortOrderEnum.DESC
