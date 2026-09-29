from datetime import datetime
from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import AwareDatetime, StringConstraints
from pydantic.experimental.missing_sentinel import MISSING

from app.enums import ConsentStatusEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Body = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ConsentDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"status"}

    id: UUID
    kind: str
    version: int
    title: str
    body: str
    is_required: bool
    published_at: datetime
    status: ConsentStatusEnum | None


class ConsentResponse(BaseResponse):
    data: ConsentDTO


class ConsentListResponse(BaseResponse):
    data: list[ConsentDTO]


class CreateConsentRequest(BaseRequest):
    kind: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
    title: Title
    body: Body
    is_required: bool
    published_at: AwareDatetime


class UpdateConsentRequest(BaseRequest):
    title: Title | MISSING = MISSING
    body: Body | MISSING = MISSING
    is_required: bool | MISSING = MISSING
    published_at: AwareDatetime | MISSING = MISSING


class UserConsentDTO(CustomBaseModel):
    consent_id: UUID
    kind: str
    version: int
    status: ConsentStatusEnum
    decided_at: datetime


class UserConsentResponse(BaseResponse):
    data: UserConsentDTO


class UserConsentListResponse(BaseResponse):
    data: list[UserConsentDTO]


class SaveUserConsentRequest(BaseRequest):
    consent_id: UUID
    status: ConsentStatusEnum
