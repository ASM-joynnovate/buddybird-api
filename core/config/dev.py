from pydantic_settings import SettingsConfigDict

from core.config.base import CommonSettings, LogFormat, LogLevel


class DevSettings(CommonSettings):
    DEBUG: bool = True
    PROFILING_ENABLED: bool = True
    SQLALCHEMY_ECHO: bool = True

    DB_SSL_MODE: str = "require"

    LOG_LEVEL: LogLevel = "DEBUG"
    LOG_FORMAT: LogFormat = "uvicorn"
    LOG_DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
