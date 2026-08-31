import pickle
from typing import Any

import orjson

from core.helpers.cache.base import BaseBackend
from core.helpers.redis import RedisHelper, RedisStatus


class RedisBackend(BaseBackend):
    def __init__(self, *, redis_helper: RedisHelper):
        self._redis_helper = redis_helper

    async def get(self, *, key: str) -> Any:
        if self._redis_helper.get_status() == RedisStatus.DOWN:
            return None

        result = await self._redis_helper.get(key=key)
        if not result:
            return None

        try:
            return orjson.loads(result)
        except Exception:
            return pickle.loads(result)  # noqa: S301

    async def set(self, *, response: Any, key: str, ttl: int = 60) -> None:
        if self._redis_helper.get_status() == RedisStatus.DOWN:
            return

        response = orjson.dumps(response) if isinstance(response, dict) else pickle.dumps(response)

        await self._redis_helper.setex(key=key, value=response, seconds=ttl)
        return

    async def delete_include(self, *, value: str) -> None:
        if self._redis_helper.get_status() == RedisStatus.DOWN:
            return

        await self._redis_helper.delete_with_wildcard(v=f"*{value}*")
        return

    async def delete_startwith(self, *, value: str) -> None:
        if self._redis_helper.get_status() == RedisStatus.DOWN:
            return

        await self._redis_helper.delete_with_wildcard(v=f"{value}*")
        return
