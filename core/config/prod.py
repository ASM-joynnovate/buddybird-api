from dataclasses import field

from pydantic_settings import SettingsConfigDict

from .base import CommonSettings, LogFormat


class ProdSettings(CommonSettings):
    DEBUG: bool = False
    PROFILING_ENABLED: bool = False
    MULTITENANCY_ENABLED: bool = True

    DB_SSL_MODE: str = "require"

    FRONTEND_CORS_ORIGIN: list[str] = field(default_factory=list)

    DOCS_URL: str | None = None
    REDOC_URL: str | None = None
    OPENAPI_URL: str | None = None

    LOG_FORMAT: LogFormat = "json"

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.prod"),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
