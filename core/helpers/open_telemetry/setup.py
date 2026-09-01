import logging

from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider

from core.fastapi import ExtendedFastAPI
from core.helpers.open_telemetry.processors import FilteredSpanProcessor

logger = logging.getLogger(__name__)


def setup_opentelemetry(app: ExtendedFastAPI) -> None:
    if not app.settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        logger.warning("OpenTelemetry exporter endpoint is not set. Skipping OpenTelemetry setup.")
        return

    resource = Resource.create(
        attributes={
            SERVICE_NAME: app.settings.SERVICE_NAME,
            "host.id": app.settings.HOSTNAME,
            "host.name": app.settings.SERVERNAME,
            "deployment.environment": app.env,
        }
    )

    # 오픈텔레메트리 로깅 설정
    logger_provider = LoggerProvider(resource=resource)
    exporter = OTLPLogExporter(
        endpoint=app.settings.OTEL_EXPORTER_OTLP_ENDPOINT + "/v1/logs",
    )
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    set_logger_provider(logger_provider)

    # 오픈텔레메트리 트레이싱 설정
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    trace_exporter = OTLPSpanExporter(endpoint=app.settings.OTEL_EXPORTER_OTLP_ENDPOINT + "/v1/traces")
    tracer_provider.add_span_processor(FilteredSpanProcessor(trace_exporter))

    # 오픈텔레메트리 메트릭 설정
    metrics_exporter = OTLPMetricExporter(endpoint=app.settings.OTEL_EXPORTER_OTLP_ENDPOINT + "/v1/metrics")
    metric_provider = MeterProvider(resource=resource, metric_readers=[PeriodicExportingMetricReader(metrics_exporter)])

    set_meter_provider(metric_provider)
