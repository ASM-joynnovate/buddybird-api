from datetime import datetime
from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import StringConstraints
from pydantic.experimental.missing_sentinel import MISSING

from app.enums import PlatformEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, I18nBodyRequest, I18nDTO

Version = Annotated[
    str, StringConstraints(max_length=12, pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
]


class AppUpdateLatestDTO(CustomBaseModel):
    version: str
    release_notes: list[str]


class AppUpdateMinSupportedDTO(CustomBaseModel):
    version: str


class AppUpdateDTO(CustomBaseModel):
    latest: AppUpdateLatestDTO
    min_supported: AppUpdateMinSupportedDTO


class AppUpdateResponse(BaseResponse):
    data: AppUpdateDTO


class BackofficeAppUpdateDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"release_notes"}

    id: UUID
    platform: PlatformEnum
    version: str
    is_forced: bool
    release_notes: I18nDTO | None
    created_at: datetime


class BackofficeAppUpdateResponse(BaseResponse):
    data: BackofficeAppUpdateDTO


class BackofficeAppUpdateListResponse(BaseResponse):
    data: list[BackofficeAppUpdateDTO]


class BackofficeAppUpdateListParams(BaseRequest):
    platform: PlatformEnum


class CreateAppUpdateRequest(BaseRequest):
    null_fields: ClassVar[set] = {"release_notes"}

    platform: PlatformEnum
    version: Version
    is_forced: bool
    release_notes: I18nBodyRequest | None


class UpdateAppUpdateRequest(BaseRequest):
    null_fields: ClassVar[set] = {"release_notes"}

    version: Version | MISSING = MISSING
    is_forced: bool | MISSING = MISSING
    release_notes: I18nBodyRequest | MISSING | None = MISSING
