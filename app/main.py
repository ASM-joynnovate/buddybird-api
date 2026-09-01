import logging
import tomllib
from pathlib import Path

from fastapi.responses import JSONResponse

from app.container import AppContainer
from core.config import config, get_env
from core.db.sqlalchemy import init_orm_mappers
from core.fastapi import ExtendedFastAPI
from core.fastapi.lifespan import lifespan
from core.fastapi.listener import register_handlers
from core.fastapi.middlewares import make_middleware
from core.fastapi.open_telemetry import setup_fastapi_opentelemetry
from core.fastapi.router import register_routers
from core.helpers.logging import setup_logging
from core.helpers.open_telemetry import setup_opentelemetry


def create_app() -> ExtendedFastAPI:
    env = get_env()
    container = AppContainer()

    init_orm_mappers()

    app_ = ExtendedFastAPI(
        title="BuddyBird API",
        description="""
버디버드 API
        """,
        middleware=make_middleware(),
        version=tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())["project"]["version"],
        env=env,
        settings=config,
        lifespan=lifespan,
        docs_url=config.DOCS_URL,
        redoc_url=config.REDOC_URL,
        openapi_url=config.OPENAPI_URL,
        swagger_ui_parameters={"docExpansion": "none"},
        default_response_class=JSONResponse,
    )

    app_.container = container

    setup_logging(app_)

    setup_opentelemetry(app_)
    setup_fastapi_opentelemetry(app_)

    register_routers(app_)
    register_handlers(app_)

    logger = logging.getLogger(__name__)
    logger.info("Starting application with env: %s", env)

    return app_


app = create_app()
