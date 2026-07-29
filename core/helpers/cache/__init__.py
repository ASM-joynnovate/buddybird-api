from .cache_manager import Cache
from .cache_tag import CacheTag
from .custom_key_maker import CustomKeyMaker
from .redis_backend import RedisBackend


def init_cache() -> None:
    Cache.init(backend=RedisBackend(), key_maker=CustomKeyMaker())


__all__ = [
    "Cache",
    "RedisBackend",
    "CustomKeyMaker",
    "CacheTag",
    "init_cache"
]
