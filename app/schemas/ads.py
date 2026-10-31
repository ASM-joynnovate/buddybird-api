from datetime import datetime
from typing import Annotated, ClassVar, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints, field_validator, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.enums import AdClickTargetEnum, AdEventKindEnum, AdImageKindEnum, AdKindEnum, AdStatusEnum, FeedItemKindEnum
from app.schemas.base import (
    BaseRequest,
    BaseResponse,
    Country,
    CustomBaseModel,
    I18nBodyRequest,
    I18nDTO,
    I18nTitleRequest,
    PageParams,
    PublicFileDTO,
    UpdateI18nBodyRequest,
    UpdateI18nTitleRequest,
    UploadRequest,
)

Color = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]


class AdListParams(BaseRequest):
    kind: Literal[AdKindEnum.HOME_BANNER]


class HomeBannerAdDTO(CustomBaseModel):
    id: UUID
    serve_id: UUID
    is_ad: bool
    advertiser_name: str
    link_url: str
    image_file: PublicFileDTO


class HomeBannerAdListResponse(BaseResponse):
    data: list[HomeBannerAdDTO]


class FeedAdDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"advertiser_description"}

    id: UUID
    kind: Literal[FeedItemKindEnum.AD]
    serve_id: UUID
    is_ad: bool
    advertiser_name: str
    advertiser_description: str | None
    advertiser_photo_file: PublicFileDTO
    link_url: str
    body: str
    image_file: PublicFileDTO
    button_text: str
    button_color: str
    button_text_color: str


class AdEventRequest(BaseRequest):
    null_fields: ClassVar[set] = {"click_target", "visible_duration_ms"}

    ad_id: UUID
    serve_id: UUID
    kind: AdEventKindEnum
    position: int = Field(ge=0)
    click_target: AdClickTargetEnum | None = None
    visible_duration_ms: int | None = Field(None, ge=0)
    occurred_at: AwareDatetime


class AddAdEventsRequest(BaseRequest):
    events: list[AdEventRequest] = Field(..., min_length=1, max_length=500)


class BackofficeAdFileDTO(PublicFileDTO):
    file_id: UUID


class AdEventCountDTO(CustomBaseModel):
    kind: AdEventKindEnum
    count: int


class BackofficeAdDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {
        "ends_at",
        "display_order",
        "advertiser_description",
        "advertiser_photo_file",
        "body",
        "button_text",
        "button_color",
        "button_text_color",
    }

    id: UUID
    kind: AdKindEnum
    status: AdStatusEnum
    is_ad: bool
    is_enabled: bool
    starts_at: datetime
    ends_at: datetime | None
    weight: int
    display_order: int | None
    countries: list[str]
    advertiser_name: I18nDTO
    advertiser_description: I18nDTO | None
    advertiser_photo_file: BackofficeAdFileDTO | None
    link_url: I18nDTO
    image_file: BackofficeAdFileDTO
    body: I18nDTO | None
    button_text: I18nDTO | None
    button_color: str | None
    button_text_color: str | None
    event_counts: list[AdEventCountDTO]


class BackofficeAdResponse(BaseResponse):
    data: BackofficeAdDTO


class BackofficeAdListResponse(BaseResponse):
    data: list[BackofficeAdDTO]


class BackofficeAdListParams(PageParams):
    kind: AdKindEnum | None = None
    status: AdStatusEnum | None = None
    is_ad: bool | None = None
    country: Country | None = None


class CreateAdRequest(BaseRequest):
    null_fields: ClassVar[set] = {
        "ends_at",
        "advertiser_description",
        "advertiser_photo_file_id",
        "body",
        "button_text",
        "button_color",
        "button_text_color",
    }

    kind: AdKindEnum
    is_ad: bool
    is_enabled: bool = True
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None
    weight: int = Field(1, ge=1, le=100)
    countries: set[Country]
    advertiser_name: I18nTitleRequest
    advertiser_description: I18nBodyRequest | None = None
    advertiser_photo_file_id: UUID | None = None
    link_url: I18nBodyRequest
    image_file_id: UUID
    body: I18nBodyRequest | None = None
    button_text: I18nTitleRequest | None = None
    button_color: Color | None = None
    button_text_color: Color | None = None

    @field_validator("link_url")
    @classmethod
    def validate_link_url(cls, value: I18nBodyRequest) -> I18nBodyRequest:
        if any(not url.startswith(("http://", "https://")) for url in value.model_dump().values() if url is not None):
            raise ValueError("링크는 http:// 또는 https://로 시작해야 합니다.")

        return value

    @model_validator(mode="after")
    def validate_period(self) -> CreateAdRequest:
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("노출 종료 시각은 노출 시작 시각보다 늦어야 합니다.")

        return self


class UpdateAdRequest(BaseRequest):
    null_fields: ClassVar[set] = {
        "ends_at",
        "advertiser_description",
        "advertiser_photo_file_id",
        "body",
        "button_text",
        "button_color",
        "button_text_color",
    }

    is_ad: bool | MISSING = MISSING
    is_enabled: bool | MISSING = MISSING
    starts_at: AwareDatetime | MISSING = MISSING
    ends_at: AwareDatetime | MISSING | None = MISSING
    weight: int | MISSING = Field(MISSING, ge=1, le=100)
    countries: set[Country] | MISSING = MISSING
    advertiser_name: UpdateI18nTitleRequest | MISSING = MISSING
    advertiser_description: UpdateI18nBodyRequest | MISSING | None = MISSING
    advertiser_photo_file_id: UUID | MISSING | None = MISSING
    link_url: UpdateI18nBodyRequest | MISSING = MISSING
    image_file_id: UUID | MISSING = MISSING
    body: UpdateI18nBodyRequest | MISSING | None = MISSING
    button_text: UpdateI18nTitleRequest | MISSING | None = MISSING
    button_color: Color | MISSING | None = MISSING
    button_text_color: Color | MISSING | None = MISSING

    @field_validator("link_url")
    @classmethod
    def validate_link_url(cls, value: UpdateI18nBodyRequest) -> UpdateI18nBodyRequest:
        if any(
            not url.startswith(("http://", "https://"))
            for url in value.model_dump(exclude_unset=True).values()
            if url is not None
        ):
            raise ValueError("링크는 http:// 또는 https://로 시작해야 합니다.")

        return value


class AdImageUploadRequest(UploadRequest):
    kind: AdImageKindEnum


class AdHourlyStatDTO(AdEventCountDTO):
    occurred_hour: datetime


class BackofficeAdStatsResponse(BaseResponse):
    data: list[AdHourlyStatDTO]
