from typing import Any

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.metrics import get_meter_provider
from opentelemetry.trace import Span, get_tracer_provider

from core.fastapi import ExtendedFastAPI


def client_request_hook(span: Span, scope: dict[str, Any], message: dict[str, Any]) -> None:
    if span and span.is_recording():
        span.set_attribute("http.method", scope["method"])
        span.set_attribute("http.url", scope["path"])

        if message.get("body"):
            span.set_attribute("http.request.body", message.get("body"))


def client_response_hook(span: Span, scope: dict[str, Any], message: dict[str, Any]) -> None:
    if span and span.is_recording():
        span.set_attribute("http.method", scope["method"])
        span.set_attribute("http.url", scope["path"])

        if message.get("body"):
            span.set_attribute("http.response.body", message.get("body"))
        if message.get("status_code"):
            span.set_attribute("http.status_code", message.get("status_code"))


def setup_fastapi_opentelemetry(app: ExtendedFastAPI) -> None:
    otel_tracer_provider = get_tracer_provider()
    otel_meter_provider = get_meter_provider()

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=otel_tracer_provider,
        meter_provider=otel_meter_provider,
        client_request_hook=client_request_hook,
        client_response_hook=client_response_hook,
        excluded_urls="healthz,docs,redoc,openapi.json",
    )
