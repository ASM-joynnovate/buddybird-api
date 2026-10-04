import sentry_sdk
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger, ignore_logger_for_sentry_logs
from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

from app.config import config


def traces_sampler(context: dict) -> float:
    if context.get("parent_sampled") is not None:
        return float(context["parent_sampled"])

    if context.get("asgi_scope", {}).get("path") == "/api/healthz":
        return 0.0

    if context.get("transaction_context", {}).get("name") == "run_periodic_command":
        return 0.01

    return config.SENTRY_TRACES_SAMPLE_RATE


def init() -> None:
    ignore_logger("uvicorn.error")
    ignore_logger_for_sentry_logs("sqlalchemy.engine*")
    ignore_logger_for_sentry_logs("uvicorn.access")

    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        environment=config.ENV,
        release=f"buddybird-api@{config.VERSION}",
        traces_sampler=traces_sampler,
        profile_session_sample_rate=1.0,
        profile_lifecycle="trace",
        integrations=[LoggingIntegration(capture_sentry_logs=True)],
        disabled_integrations=[AsyncPGIntegration()],
        max_request_body_size="never",
        event_scrubber=EventScrubber(
            denylist=[
                *DEFAULT_DENYLIST,
                "access_token",
                "refresh_token",
                "id_token",
                "identity_token",
                "authorization_code",
            ],
            recursive=True,
        ),
    )
