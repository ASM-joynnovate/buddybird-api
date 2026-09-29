import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference
from starlette.middleware.authentication import AuthenticationMiddleware

from app import sentry
from app.config import config
from app.db import engine
from app.errors import register_exception_handlers
from app.legacy.routers import captures, labels
from app.middlewares import AuthBackend, IdempotencyMiddleware, NoStoreMiddleware
from app.oauth.base import http_client
from app.routers import (
    auth,
    consents,
    devices,
    feedback,
    notices,
    notifications,
    parrots,
    sessions,
    settings,
    user_consents,
    user_parrot_sounds,
    users,
    words,
)
from app.s3 import s3


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=config.LOG_LEVEL)

    try:
        yield
    finally:
        await engine.dispose()
        await http_client.aclose()

        s3.close()


def create_app() -> FastAPI:
    sentry.init()

    application = FastAPI(
        title="BuddyBird API",
        description="\n버디버드 API\n        ",
        version=config.VERSION,
        lifespan=lifespan,
        docs_url=config.DOCS_URL,
        redoc_url=config.REDOC_URL,
        openapi_url=config.OPENAPI_URL,
        swagger_ui_parameters={"docExpansion": "none"},
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=config.FRONTEND_CORS_ORIGIN,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            ),
            Middleware(NoStoreMiddleware),
            Middleware(CorrelationIdMiddleware),
            Middleware(AuthenticationMiddleware, backend=AuthBackend()),
            Middleware(IdempotencyMiddleware),
        ],
    )

    register_exception_handlers(application)

    application.include_router(labels.router, prefix="/api/v1/backoffice", tags=["백오피스"])
    application.include_router(captures.router, prefix="/api/v1/backoffice", tags=["백오피스"])
    application.include_router(auth.router, prefix="/api/v1", tags=["인증"])
    application.include_router(users.router, prefix="/api/v1", tags=["사용자"])
    application.include_router(settings.router, prefix="/api/v1", tags=["설정"])
    application.include_router(consents.router, prefix="/api/v1", tags=["동의"])
    application.include_router(user_consents.router, prefix="/api/v1", tags=["동의"])
    application.include_router(devices.router, prefix="/api/v1", tags=["기기"])
    application.include_router(parrots.router, prefix="/api/v1", tags=["앵무새"])
    application.include_router(words.router, prefix="/api/v1", tags=["단어"])
    application.include_router(sessions.router, prefix="/api/v1", tags=["세션"])
    application.include_router(user_parrot_sounds.router, prefix="/api/v1", tags=["세션"])
    application.include_router(feedback.router, prefix="/api/v1", tags=["피드백"])
    application.include_router(notices.router, prefix="/api/v1", tags=["공지"])
    application.include_router(notifications.router, prefix="/api/v1", tags=["알림"])

    @application.get("/api/healthz", tags=["공통"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/api/scalar", include_in_schema=False)
    async def scalar_html() -> HTMLResponse:
        return get_scalar_api_reference(openapi_url=application.openapi_url, title=application.title)

    return application


app = create_app()
