import pickle
from typing import Any

import orjson

from core.helpers.cache.base import BaseBackend
from core.helpers.redis import RedisHelper, RedisStatus


class RedisBackend(BaseBackend):
    async def get(self, *, key: str) -> Any:
        if RedisHelper().get_status() == RedisStatus.DOWN:
            return None

        result = await RedisHelper().get(key)
        if not result:
            return None

        try:
            return orjson.loads(result)
        except Exception:
            return pickle.loads(result)

    async def set(self, *, response: Any, key: str, ttl: int = 60) -> None:
        if RedisHelper().get_status() == RedisStatus.DOWN:
            return

        if isinstance(response, dict):
            response = orjson.dumps(response)
        else:
            response = pickle.dumps(response)

        await RedisHelper().setex(key=key, value=response, seconds=ttl)
        return

    async def delete_include(self, *, value: str) -> None:
        if RedisHelper().get_status() == RedisStatus.DOWN:
            return

        await RedisHelper().delete_with_wildcard(f"*{value}*")
        return

    async def delete_startwith(self, *, value: str) -> None:
        if RedisHelper().get_status() == RedisStatus.DOWN:
            return

        await RedisHelper().delete_with_wildcard(f"{value}*")
        return
