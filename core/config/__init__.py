import os
from enum import StrEnum
from functools import lru_cache

from .dev import DevSettings
from .local import LocalSettings
from .prod import ProdSettings
from .test import TestSettings


class Env(StrEnum):
    prod = "prod"
    dev = "dev"
    local = "local"
    test = "test"


def get_env():
    return os.getenv("BUDDYBIRD_ENV")


@lru_cache
def get_settings():
    match get_env():
        case Env.prod:
            return ProdSettings()
        case Env.dev:
            return DevSettings()
        case Env.test:
            return TestSettings()
        case _:
            return LocalSettings()


config = get_settings()
