from typing import Literal

from pydantic_settings import BaseSettings

type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
type LogFormat = Literal["plain", "json", "uvicorn"]


class CommonSettings(BaseSettings):
    DEBUG: bool = False
    PROFILING_ENABLED: bool = False

    HOSTNAME: str = "localhost"
    SERVERNAME: str = "localhost"
    SERVICE_NAME: str = "api.buddybird"

    READER_DB_URL: str
    WRITER_DB_URL: str

    AUTH_ACCESS_TOKEN_SECRET_KEY: str
    AUTH_REFRESH_TOKEN_SECRET_KEY: str
    AUTH_ALGORITHM: str
    AUTH_ACCESS_TOKEN_EXPIRE_MINUTES: int
    AUTH_REFRESH_TOKEN_EXPIRE_MINUTES: int

    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_REGION: str
    S3_BUCKET_NAME: str
    S3_BUCKET_DOMAIN: str

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_USERNAME: str
    REDIS_PASSWORD: str

    SQLALCHEMY_ECHO: bool = False
    FRONTEND_CORS_ORIGIN: list[str] = []

    OPENAPI_URL: str | None = "/api/openapi.json"
    DOCS_URL: str | None = "/api/docs"
    REDOC_URL: str | None = "/api/redoc"

    CELERY_BROKER_URL: str
    CELERY_BACKEND_URL: str

    LOG_LEVEL: LogLevel = "INFO"
    LOG_FORMAT: LogFormat = "plain"
    LOG_DEBUG: bool = False

    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
