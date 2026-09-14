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


class DuplicateLabelCategoryError(CustomError):
    code = 409
    error_code = "AUDIO_CAPTURE__DUPLICATE_LABEL_CATEGORY"
    message = "동일한 이름과 대상을 가진 라벨 카테고리가 이미 존재합니다."


class DuplicateLabelOptionError(CustomError):
    code = 409
    error_code = "AUDIO_CAPTURE__DUPLICATE_LABEL_OPTION"
    message = "동일한 이름의 라벨 옵션이 이미 존재합니다."


class DuplicateReviewAudioFileIdError(CustomError):
    code = 400
    error_code = "AUDIO_CAPTURE__DUPLICATE_REVIEW_AUDIO_FILE_ID"
    message = "중복된 리뷰 오디오 파일 ID가 있습니다."


class InvalidAudioSegmentRangeError(CustomError):
    code = 400
    error_code = "AUDIO_CAPTURE__INVALID_SEGMENT_RANGE"
    message = "세그먼트 끝 위치는 시작 위치보다 커야 합니다."


class InvalidLabelCategoryTargetError(CustomError):
    code = 400
    error_code = "AUDIO_CAPTURE__INVALID_LABEL_CATEGORY_TARGET"
    message = "이 라벨은 해당 대상에 지정할 수 없습니다."


class FileSizeExceededError(CustomError):
    code = 400
    error_code = "COMMON__FILE_SIZE_EXCEEDED"
    message = "파일 크기가 허용된 최대 크기를 초과했습니다."


class BackofficePasswordMissingError(CustomError):
    code = 401
    error_code = "AUDIO_CAPTURE__BACKOFFICE_PASSWORD_MISSING"
    message = "백오피스 비밀번호를 입력해 주세요."


class BackofficePasswordInvalidError(CustomError):
    code = 401
    error_code = "AUDIO_CAPTURE__BACKOFFICE_PASSWORD_INVALID"
    message = "백오피스 비밀번호가 올바르지 않습니다."


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
    async def request_validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        content: dict[str, Any] = {
            "error_code": "COMMON__REQUEST_VALIDATION_ERROR",
            "message": "요청값 검증 오류가 발생했습니다.",
        }

        if config.ENV != "prod":
            content["detail"] = {"body": exc.body, "errors": exc.errors()}

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(content),
        )

    @app.exception_handler(Exception)
    async def internal_server_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error("서버 내부 오류", exc_info=exc)
        content: dict[str, Any] = {
            "error_code": "COMMON__INTERNAL_SERVER_ERROR",
            "message": "서버 내부 오류가 발생했습니다.",
        }

        if config.ENV == "prod":
            content["message"] = "서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요."
        else:
            content["detail"] = str(exc)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(content),
        )
