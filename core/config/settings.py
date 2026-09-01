import os
from enum import StrEnum
from functools import lru_cache

from core.config.base import CommonSettings
from core.config.dev import DevSettings
from core.config.local import LocalSettings
from core.config.prod import ProdSettings
from core.config.test import TestSettings


class Env(StrEnum):
    PROD = "prod"
    DEV = "dev"
    LOCAL = "local"
    TEST = "test"


def get_env() -> str | None:
    return os.getenv("BUDDYBIRD_ENV")


@lru_cache
def get_settings() -> CommonSettings:
    match get_env():
        case Env.PROD:
            return ProdSettings()
        case Env.DEV:
            return DevSettings()
        case Env.TEST:
            return TestSettings()
        case _:
            return LocalSettings()


config = get_settings()
