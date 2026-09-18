from datetime import datetime

from pydantic import Field

from app.enums import ConsentKindEnum, ConsentStatusEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class ConsentDTO(CustomBaseModel):
    kind: ConsentKindEnum
    notice_version: int
    status: ConsentStatusEnum
    decided_at: datetime


class ConsentResponse(BaseResponse):
    data: ConsentDTO


class ConsentListResponse(BaseResponse):
    data: list[ConsentDTO]


class SaveConsentRequest(BaseRequest):
    kind: ConsentKindEnum
    notice_version: int = Field(..., ge=1)
    status: ConsentStatusEnum
