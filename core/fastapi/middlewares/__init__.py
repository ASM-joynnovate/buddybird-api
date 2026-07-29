from asgi_correlation_id import CorrelationIdMiddleware
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware

from core.config import config

from .etag import ETagMiddleware
from .sqlalchemy import SQLAlchemyMiddleware


def make_middleware() -> list[Middleware]:
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=config.FRONTEND_CORS_ORIGIN,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        Middleware(ETagMiddleware),
        Middleware(CorrelationIdMiddleware),
        Middleware(SQLAlchemyMiddleware)
    ]

    return middleware


__all__ = [
    "make_middleware",
    "SQLAlchemyMiddleware",
]
