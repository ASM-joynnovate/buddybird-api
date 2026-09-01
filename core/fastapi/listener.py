import logging

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from starlette import status

from core.common.errors.base import CustomError
from core.config import Env
from core.fastapi import ExtendedFastAPI

logger = logging.getLogger(__name__)


def register_exception_handlers(app: ExtendedFastAPI) -> None:
    @app.exception_handler(CustomError)
    async def custom_exception_handler(_: Request, exc: CustomError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.code,
            content={"error_code": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(ResponseValidationError)
    async def response_validation_exception_handler(_: Request, exc: ResponseValidationError) -> JSONResponse:
        logger.error(
            "exception",
            extra={
                "data": {
                    "exception_class": exc,
                    "errors": exc.errors,
                    # "body": exc.body
                }
            },
        )

        if app.env == Env.PROD:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=jsonable_encoder(
                    {
                        "error_code": "COMMON__RESPONSE_VALIDATION_ERROR",
                        "message": "반환값 검증 오류가 발생했습니다. 관리자에게 문의해주세요.",
                    }
                ),
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(
                {"error_code": "COMMON__RESPONSE_VALIDATION_ERROR", "message": "반환값 검증 오류가 발생했습니다."}
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        if app.env == Env.PROD:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=jsonable_encoder(
                    {
                        "error_code": "COMMON__REQUEST_VALIDATION_ERROR",
                        "message": "요청값 검증 오류가 발생했습니다.",
                    }
                ),
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder(
                {
                    "error_code": "COMMON__REQUEST_VALIDATION_ERROR",
                    "message": "요청값 검증 오류가 발생했습니다.",
                    "detail": {"body": exc.body, "errors": exc.errors()},
                }
            ),
        )

    @app.exception_handler(Exception)
    async def internal_server_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.error("exception", extra={"data": {"exception_class": exc, "message": str(exc)}})

        if app.env == Env.PROD:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=jsonable_encoder(
                    {
                        "error_code": "COMMON__INTERNAL_SERVER_ERROR",
                        "message": "서버 내부 오류가 발생했습니다. 관리자에게 문의해주세요.",
                    }
                ),
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(
                {
                    "error_code": "COMMON__INTERNAL_SERVER_ERROR",
                    "message": "서버 내부 오류가 발생했습니다.",
                    "detail": str(exc),
                }
            ),
        )


def register_handlers(app: ExtendedFastAPI) -> None:
    register_exception_handlers(app)
