from typing import ClassVar

from pydantic_settings import SettingsConfigDict

from .base import CommonSettings, LogFormat, LogLevel


class LocalSettings(CommonSettings):
    DEBUG: bool = True
    PROFILING_ENABLED: bool = True
    SQLALCHEMY_ECHO: bool = True

    FRONTEND_CORS_ORIGIN: ClassVar[list[str]] = ["http://localhost:3000", "http://localhost:3001"]

    REDIS_ENABLED: bool = True

    LOG_LEVEL: LogLevel = "DEBUG"
    LOG_FORMAT: LogFormat = "uvicorn"
    LOG_DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
