import inspect
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from opentelemetry import trace

from core.helpers.cache.base import BaseBackend, BaseKeyMaker
from core.helpers.cache.cache_tag import CacheTag


class CacheManager:
    def __init__(self, *, backend: BaseBackend, key_maker: BaseKeyMaker):
        self.backend = backend
        self.key_maker = key_maker
        self.tracer = trace.get_tracer(__name__)
        self._logger = logging.getLogger(__name__)

    def cached(
        self,
        *,
        prefix: str | None = None,
        tag: CacheTag | None = None,
        ttl: int = 60,
    ) -> Callable:
        def _cached(function) -> Callable:
            @wraps(function)
            async def __cached(*args, **kwargs) -> Any:
                with self.tracer.start_as_current_span("cache") as span:
                    span.set_attribute("cache.function", function.__name__)
                    # 실제 호출 시의 인자들을 바인딩
                    bound_args = inspect.signature(function).bind(*args, **kwargs)
                    bound_args.apply_defaults()

                    key = await self.key_maker.make(
                        function=function, prefix=prefix or tag.value, bound_args=bound_args
                    )
                    span.set_attribute("cache.key", key)
                    try:
                        cached_response = await self.backend.get(key=key)
                        if cached_response:
                            self._logger.debug("Cache hit for key: %s", key)
                            span.set_attribute("cache.hit", True)

                            return cached_response
                    except Exception as e:
                        span.record_exception(e)

                    response = await function(*args, **kwargs)
                    span.set_attribute("cache.hit", False)
                    self._logger.info("Cache miss for key: %s", key)
                    try:
                        await self.backend.set(response=response, key=key, ttl=ttl)
                    except Exception as e:
                        span.record_exception(e)
                    return response

            return __cached

        return _cached

    async def remove_by_tag(self, *, key: CacheTag) -> None:
        await self.backend.delete_include(value=key.value)

    async def remove_by_prefix(self, *, key: str) -> None:
        await self.backend.delete_startwith(value=key)

    async def remove_by_contains(self, *, key: str) -> None:
        await self.backend.delete_include(value=key)
