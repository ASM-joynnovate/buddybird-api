from fastapi import FastAPI

from core.config import Env
from core.config.base import CommonSettings


class ExtendedFastAPI(FastAPI):
    def __init__(
            self,
            env: Env,
            settings: CommonSettings,
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.env = env
        self.settings = settings
