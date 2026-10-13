from typing import ClassVar

from app.schemas.base import BaseResponse, CustomBaseModel


class IceServerDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"username", "credential"}

    urls: list[str]
    username: str | None
    credential: str | None


class TurnCredentialDTO(CustomBaseModel):
    ice_servers: list[IceServerDTO]


class TurnCredentialResponse(BaseResponse):
    data: TurnCredentialDTO
