import logging
import tomllib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference
from starlette.middleware.authentication import AuthenticationMiddleware

from app.config import config
from app.db import engine
from app.errors import register_exception_handlers
from app.legacy.routers import captures, labels
from app.middlewares import AuthBackend, ETagMiddleware, IdempotencyMiddleware, NoStoreMiddleware
from app.oauth.base import http_client
from app.routers import auth, consents, devices, parrots, sessions, settings, users, words
from app.s3 import get_s3


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=config.LOG_LEVEL)

    try:
        yield
    finally:
        await engine.dispose()
        await http_client.aclose()

        get_s3().close()
        get_s3.cache_clear()


def create_app() -> FastAPI:
    application = FastAPI(
        title="BuddyBird API",
        description="\n버디버드 API\n        ",
        version=tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())["project"]["version"],
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
            Middleware(ETagMiddleware),
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
    application.include_router(devices.router, prefix="/api/v1", tags=["기기"])
    application.include_router(parrots.router, prefix="/api/v1", tags=["앵무새"])
    application.include_router(words.router, prefix="/api/v1", tags=["단어"])
    application.include_router(sessions.router, prefix="/api/v1", tags=["세션"])

    @application.get("/api/healthz", tags=["공통"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/api/scalar", include_in_schema=False)
    async def scalar_html() -> HTMLResponse:
        return get_scalar_api_reference(openapi_url=application.openapi_url, title=application.title)

    return application


app = create_app()
