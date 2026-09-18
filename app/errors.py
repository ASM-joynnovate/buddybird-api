import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from starlette import status

from app.config import config

logger = logging.getLogger(__name__)


class CustomError(Exception):
    code = 400
    error_code = "COMMON__BAD_REQUEST"
    message = "잘못된 요청입니다."

    def __init__(self, message: str | None = None):
        if message:
            self.message = message


class ResourceNotFoundError(CustomError):
    code = 404
    error_code = "COMMON__RESOURCE_NOT_FOUND"
    message = "요청한 리소스를 찾을 수 없습니다."


class AuthenticationError(CustomError):
    code = 401
    error_code = "AUTH__INVALID_TOKEN"
    message = "인증에 실패했습니다."


class AuthenticationServiceUnavailableError(CustomError):
    code = 503
    error_code = "AUTH__SERVICE_UNAVAILABLE"
    message = "인증 서비스를 일시적으로 사용할 수 없습니다."


class UserSaveUnavailableError(CustomError):
    code = 503
    error_code = "USER__SAVE_UNAVAILABLE"
    message = "사용자 정보를 일시적으로 저장할 수 없습니다."


class OAuthCredentialError(CustomError):
    error_code = "AUTH__INVALID_PROVIDER_CREDENTIAL"
    message = "소셜 로그인 자격을 확인할 수 없습니다. 다시 로그인해 주세요."


class OAuthCredentialRequiredError(CustomError):
    error_code = "AUTH__PROVIDER_CREDENTIAL_REQUIRED"
    message = "소셜 로그인 자격이 필요합니다. 다시 로그인해 주세요."


class WithdrawalSaveUnavailableError(CustomError):
    code = 503
    error_code = "AUTH__WITHDRAWAL_SAVE_UNAVAILABLE"
    message = "탈퇴 접수 결과를 확인할 수 없습니다. 다시 요청해 주세요."


class WithdrawalOperationError(Exception):
    def __init__(self, error_code: str, *, retryable: bool = False):
        super().__init__(error_code)
        self.error_code = error_code
        self.retryable = retryable


class DuplicateNicknameError(CustomError):
    code = 409
    error_code = "USER__DUPLICATE_NICKNAME"
    message = "이미 사용 중인 닉네임입니다."


class InvalidProfilePhotoError(CustomError):
    code = 400
    error_code = "USER__INVALID_PROFILE_PHOTO"
    message = "JPEG 또는 PNG 이미지만 업로드할 수 있습니다."


class ProfilePhotoServiceUnavailableError(CustomError):
    code = 503
    error_code = "USER__PHOTO_SERVICE_UNAVAILABLE"
    message = "프로필 사진을 일시적으로 저장할 수 없습니다."


class FileSizeExceededError(CustomError):
    code = 400
    error_code = "COMMON__FILE_SIZE_EXCEEDED"
    message = "파일 크기가 허용된 최대 크기를 초과했습니다."


class IdempotencyKeyRequiredError(CustomError):
    code = 400
    error_code = "COMMON__IDEMPOTENCY_KEY_REQUIRED"
    message = "Idempotency-Key 헤더에 UUID가 필요합니다."


class DeviceNotRegisteredError(CustomError):
    code = 400
    error_code = "DEVICE__NOT_REGISTERED"
    message = "등록되지 않은 기기입니다."


class DeviceNotStationError(CustomError):
    code = 403
    error_code = "DEVICE__NOT_STATION"
    message = "station 기기만 요청할 수 있습니다."


class DeviceSaveUnavailableError(CustomError):
    code = 503
    error_code = "DEVICE__SAVE_UNAVAILABLE"
    message = "기기 정보를 일시적으로 저장할 수 없습니다."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CustomError)
    async def custom_exception_handler(_: Request, exc: CustomError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.code,
            content={"error_code": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(ResponseValidationError)
    async def response_validation_exception_handler(_: Request, exc: ResponseValidationError) -> JSONResponse:
        logger.error("반환값 검증 오류", exc_info=exc)
        message = "반환값 검증 오류가 발생했습니다."

        if config.ENV == "prod":
            message = "반환값 검증 오류가 발생했습니다. 관리자에게 문의해주세요."

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error_code": "COMMON__RESPONSE_VALIDATION_ERROR", "message": message},
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        content: dict[str, Any] = {
            "error_code": "COMMON__REQUEST_VALIDATION_ERROR",
            "message": "요청값 검증 오류가 발생했습니다.",
        }

        if config.ENV != "prod" and request.url.path != "/api/v1/auth/login":
            content["detail"] = {"body": exc.body, "errors": exc.errors()}

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(content),
        )

    @app.exception_handler(Exception)
    async def internal_server_error_handler(request: Request, exc: Exception) -> JSONResponse:
        auth_request = request.url.path.startswith("/api/v1/auth/")
        logger.error("서버 내부 오류", exc_info=None if auth_request else exc)
        content: dict[str, Any] = {
            "error_code": "COMMON__INTERNAL_SERVER_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        }

        if config.ENV == "prod":
            content["message"] = "서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."
        elif not auth_request:
            content["detail"] = str(exc)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(content),
        )
