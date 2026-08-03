import asyncio
import logging
from collections.abc import Awaitable
from enum import StrEnum
from typing import Any

from opentelemetry.trace import get_current_span
from redis import BusyLoadingError
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff

from core.config import config


class RedisStatus(StrEnum):
    UP = "up"
    DOWN = "down"


class RedisHelper:
    _instance = None
    _status = RedisStatus.DOWN
    _last_status = RedisStatus.DOWN

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._redis_client = Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                username=config.REDIS_USERNAME,
                password=config.REDIS_PASSWORD,
                decode_responses=False,
                max_connections=100,
                socket_timeout=30,
                socket_connect_timeout=10,
                retry=Retry(ExponentialBackoff(), 3),
                retry_on_error=[BusyLoadingError, ConnectionError, TimeoutError],
                health_check_interval=30,
                socket_keepalive=True,
            )
            cls._logger = logging.getLogger("buddybird.redis")
        return cls._instance

    @property
    def client(self) -> Redis:
        return self._redis_client.client()

    def get_status(self) -> RedisStatus:
        return self._status

    async def ping(self):
        await self.client.ping()

    async def check_status(self):
        self._logger.debug("Checking Redis status")

        while True:
            try:
                await self.ping()
                self._status = RedisStatus.UP
            except Exception as e:
                span = get_current_span()
                span.record_exception(e)
                self._status = RedisStatus.DOWN
            finally:
                if self._status != self._last_status:
                    self._logger.info(f"Redis Status Changed [{self._last_status.value} -> {self._status.value}]")
                    self._last_status = self._status

            await asyncio.sleep(5)

    async def get(self, key: str) -> Any:
        return await self.client.get(key)

    async def set(self, key: str, value: bytes):
        return await self.client.set(key, value)

    async def setex(self, key: str, value: bytes, seconds: int):
        return await self.client.setex(key, seconds, value)

    async def delete_with_key(self, key: str):
        return await self.client.delete(key)

    async def delete_with_wildcard(self, v: str):
        client = self.client
        async for t in client.scan_iter(v):
            await client.delete(t)

    async def delete_all(self):
        await self.client.flushdb()

    async def smembers(self, key: str) -> set:
        return await self.client.smembers(key)

    async def sadd(self, name: str, value: bytes | bytearray | memoryview | str | int | float) -> Awaitable[int] | int:
        return await self.client.sadd(name, value)

    async def srem(
        self, name: str, *values: bytes | bytearray | memoryview | str | int | float
    ) -> Awaitable[int] | int:
        return await self.client.srem(name, *values)
