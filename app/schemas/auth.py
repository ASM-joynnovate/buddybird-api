from uuid import UUID

from pydantic import Field, SecretStr, model_validator

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class GoogleLoginRequest(BaseRequest):
    refresh_token: SecretStr = Field(..., min_length=1, max_length=8192)


class AppleLoginRequest(BaseRequest):
    client_id: str = Field(..., min_length=1, max_length=255)
    authorization_code: SecretStr = Field(..., min_length=1, max_length=8192)


class LoginRequest(BaseRequest):
    google: GoogleLoginRequest | None = None
    apple: AppleLoginRequest | None = None

    @model_validator(mode="after")
    def validate_provider(self) -> LoginRequest:
        if self.google is not None and self.apple is not None:
            raise ValueError("한 번에 한 제공자의 자격만 전달할 수 있습니다.")

        return self


class LoginDTO(CustomBaseModel):
    user_id: UUID
    is_new_user: bool


class LoginResponse(BaseResponse):
    data: LoginDTO
