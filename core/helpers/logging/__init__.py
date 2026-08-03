import logging.config
import sys
from collections.abc import MutableMapping

import orjson
import structlog
from asgi_correlation_id import correlation_id as ctxvar_correlation_id
from opentelemetry import trace

from core.fastapi import ExtendedFastAPI
from core.helpers.logging.open_telemetry.handler import OTELLogHandler


def extract_event_dict(_, __, event_dict: MutableMapping) -> MutableMapping:
    try:
        event_dict = event_dict | orjson.loads(event_dict["event"])
    except ValueError:
        pass
    else:
        if "request" in event_dict:
            event_dict["event"] = f"{event_dict['request']['method']} {event_dict['request']['path']}"
    return event_dict


def inject_request_id(_, __, event_dict: MutableMapping) -> MutableMapping:
    if correlation_id := ctxvar_correlation_id.get(None):
        event_dict["correlation_id"] = correlation_id
    return event_dict


def inject_open_telemetry_spans(_, __, event_dict):
    span = trace.get_current_span()
    if not span.is_recording():
        event_dict["span"] = None
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["span"] = {
        "span_id": format(ctx.span_id, "016x"),
        "trace_id": format(ctx.trace_id, "032x"),
        "parent_span_id": None if not parent else format(parent.span_id, "016x"),
    }

    return event_dict


def cleanup_event_dict(_, __, event_dict: MutableMapping) -> MutableMapping:
    event_dict.pop("_logger", None)
    event_dict.pop("_name", None)
    return event_dict


def generate_logging_config(app: ExtendedFastAPI) -> dict:
    processors = [
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f"),
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.ExtraAdder(),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer()
    ]
    if app.settings.LOG_FORMAT == "json":
        processors.append(
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.PATHNAME,
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.MODULE,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                }
            )
        )

    common_formatter_processors = processors + [
        extract_event_dict,
        inject_request_id,
        inject_open_telemetry_spans,
        cleanup_event_dict,
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
    ]
    log_level = getattr(logging, app.settings.LOG_LEVEL)
    structlog.configure(
        processors=processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    return {
        "version": 1,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": common_formatter_processors
                              + [
                                  structlog.processors.format_exc_info,
                                  structlog.processors.JSONRenderer(ensure_ascii=False),
                              ],
                "foreign_pre_chain": processors,
            },
            "colored": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": common_formatter_processors
                              + [
                                  structlog.dev.ConsoleRenderer(
                                      colors=True,
                                      exception_formatter=structlog.dev.RichTracebackFormatter(show_locals=False, max_frames=5)
                                  ),
                              ],
                "foreign_pre_chain": processors,
            },
        },
        "handlers": {
            "console": {
                "level": app.settings.LOG_LEVEL,
                "class": "logging.StreamHandler",
                "formatter": "json" if app.settings.LOG_FORMAT == "json" else "colored",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "buddybird": {
                "level": app.settings.LOG_LEVEL,
                "handlers": ["console"],
                "propagate": True,
            },
            "unicorn": {
                "level": app.settings.LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": app.settings.LOG_LEVEL,
                "handlers": ["console"],
                "propagate": False,
            }
        },
    }


def setup_logging(app: ExtendedFastAPI):
    if app.settings.LOG_FORMAT != "uvicorn":
        logging.config.dictConfig(generate_logging_config(app))

    if app.settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        otlp_handler = OTELLogHandler()
        logging.getLogger().addHandler(otlp_handler)

    if app.settings.LOG_DEBUG:
        try:
            __import__("logging_tree").printout()
        except ImportError:
            logging.warning("The logging_tree module was not found. Skipping logging debug.")
