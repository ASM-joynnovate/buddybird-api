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

from app.config import config
from app.db import engine
from app.errors import register_exception_handlers
from app.middlewares import ETagMiddleware
from app.redis import get_redis
from app.routers import captures, labels
from app.s3 import get_s3


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(level=config.LOG_LEVEL)

    redis_client = get_redis() if config.REDIS_ENABLED else None

    try:
        yield
    finally:
        await engine.dispose()

        if redis_client is not None:
            await redis_client.aclose()

            get_redis.cache_clear()

        if get_s3.cache_info().currsize:
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
            Middleware(ETagMiddleware),
            Middleware(CorrelationIdMiddleware),
        ],
    )

    register_exception_handlers(application)

    application.include_router(labels.router, prefix="/api/v1/backoffice", tags=["백오피스"])
    application.include_router(captures.router, prefix="/api/v1/backoffice", tags=["백오피스"])

    @application.get("/api/healthz", tags=["공통"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/api/scalar", include_in_schema=False)
    async def scalar_html() -> HTMLResponse:
        return get_scalar_api_reference(openapi_url=application.openapi_url, title=application.title)

    return application


app = create_app()
