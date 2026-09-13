from functools import lru_cache

# pyproject.toml에 직접 선언된 의존성이다.
# noinspection PyPackageRequirements
from redis.asyncio import Redis

from app.config import config


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    return Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        username=config.REDIS_USERNAME,
        password=config.REDIS_PASSWORD,
        decode_responses=False,
    )
