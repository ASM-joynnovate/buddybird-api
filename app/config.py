import os
from typing import ClassVar, Literal
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_env = os.getenv("ENV", "local")
_local = _env not in {"prod", "dev", "test"}
_env_file = ".env.local" if _local else f".env.{_env}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.prod") if _env == "prod" else _env_file,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENV: ClassVar[str] = _env

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_SSL_MODE: str = "require" if _env in {"dev", "prod"} else "prefer"
    SQLALCHEMY_ECHO: bool = _local or _env == "dev"

    BACKOFFICE_PASSWORD: str

    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_AUDIENCE: str = "authenticated"

    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION: str = "ap-northeast-2"
    S3_BUCKET_NAME: str

    REDIS_ENABLED: bool = _local
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_USERNAME: str = "default"
    REDIS_PASSWORD: str = ""

    FRONTEND_CORS_ORIGIN: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:3001"] if _local else []
    )
    OPENAPI_URL: str | None = None if _env == "prod" else "/api/openapi.json"
    DOCS_URL: str | None = None if _env == "prod" else "/api/docs"
    REDOC_URL: str | None = None if _env == "prod" else "/api/redoc"

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "DEBUG" if _local or _env == "dev" else "INFO"

    @property
    def DB_URL(self) -> str:  # noqa: N802
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


config = Settings()
