import asyncio
from contextlib import asynccontextmanager

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.trace import get_tracer_provider

from core.config import config
from core.db.session import EngineType, engines, sqlalchemy_instrumentor
from core.fastapi import ExtendedFastAPI
from core.helpers.redis import RedisHelper


def start():
    sqlalchemy_instrumentor.instrument(
        engine=engines.get(EngineType.READER).sync_engine,
        enable_commenter=True,
        commenter_options={},
        enable_attribute_commenter=True,
    )
    sqlalchemy_instrumentor.instrument(
        engine=engines.get(EngineType.WRITER).sync_engine,
        enable_commenter=True,
        commenter_options={},
        enable_attribute_commenter=True,
    )
    HTTPXClientInstrumentor().instrument()

    if config.REDIS_ENABLED:
        RedisInstrumentor().instrument(tracer_provider=get_tracer_provider())
        asyncio.create_task(RedisHelper().check_status())  # noqa: RUF006


def shutdown():
    if config.REDIS_ENABLED:
        RedisInstrumentor().uninstrument()

    sqlalchemy_instrumentor.uninstrument()
    HTTPXClientInstrumentor().uninstrument()
    FastAPIInstrumentor().uninstrument()


@asynccontextmanager
async def lifespan(_app: ExtendedFastAPI):
    start()
    yield
    shutdown()
