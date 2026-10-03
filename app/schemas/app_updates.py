from typing import ClassVar

from pydantic import Field

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, I18nBodyRequest, I18nDTO


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


class BackofficeAppUpdateLatestDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"release_notes"}

    version: str
    release_notes: I18nDTO | None


class BackofficeAppUpdateDTO(CustomBaseModel):
    latest: BackofficeAppUpdateLatestDTO
    min_supported: AppUpdateMinSupportedDTO


class BackofficeAppUpdateResponse(BaseResponse):
    data: BackofficeAppUpdateDTO


class SaveAppUpdateLatestRequest(BaseRequest):
    null_fields: ClassVar[set] = {"release_notes"}

    version: str = Field(..., min_length=1, max_length=12)
    release_notes: I18nBodyRequest | None


class SaveAppUpdateMinSupportedRequest(BaseRequest):
    version: str = Field(..., min_length=1, max_length=12)


class SaveAppUpdateRequest(BaseRequest):
    latest: SaveAppUpdateLatestRequest
    min_supported: SaveAppUpdateMinSupportedRequest
