from typing import Literal
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings

type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
type LogFormat = Literal["plain", "json", "uvicorn"]


class CommonSettings(BaseSettings):
    DEBUG: bool = False
    PROFILING_ENABLED: bool = False

    HOSTNAME: str = "localhost"
    SERVERNAME: str = "localhost"
    SERVICE_NAME: str = "api.buddybird"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    @property
    def WRITER_DB_URL(self) -> str:  # noqa: N802
        return self._dsn()

    @property
    def READER_DB_URL(self) -> str:  # noqa: N802
        return self._dsn()

    def _dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    AUTH_ACCESS_TOKEN_SECRET_KEY: str
    AUTH_REFRESH_TOKEN_SECRET_KEY: str
    AUTH_ALGORITHM: str
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int
    AUTH_REFRESH_TOKEN_EXPIRE_MINUTES: int

    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION: str = "ap-northeast-2"
    S3_BUCKET_NAME: str
    S3_BUCKET_DOMAIN: str

    REDIS_ENABLED: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_USERNAME: str = "default"
    REDIS_PASSWORD: str = ""

    CELERY_BROKER_URL: str | None = None
    CELERY_BACKEND_URL: str | None = None

    SQLALCHEMY_ECHO: bool = False
    FRONTEND_CORS_ORIGIN: list[str] = []

    OPENAPI_URL: str | None = "/api/openapi.json"
    DOCS_URL: str | None = "/api/docs"
    REDOC_URL: str | None = "/api/redoc"

    LOG_LEVEL: LogLevel = "INFO"
    LOG_FORMAT: LogFormat = "plain"
    LOG_DEBUG: bool = False

    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
