import inspect
from functools import update_wrapper

from opentelemetry import trace
from opentelemetry.trace import StatusCode
from pydantic import BaseModel


class OpenTelemetryTrace:
    def __init__(
        self,
        name: str = None,
        redact_keys: list[str] = None,
        max_depth: int = 5,
        max_length: int = 200,
        include_args: bool = True,
    ):
        self.name = name
        self.redact_keys = redact_keys or []
        self.max_depth = max_depth
        self.max_length = max_length
        self.include_args = include_args
        self.tracer = trace.get_tracer(__name__)

        self.redact_keys += [
            "password",
            "token",
            "access_token",
            "refresh_token",
        ]

    def __call__(self, func):
        is_async = inspect.iscoroutinefunction(func)

        def _flatten_and_set(span, prefix, value, depth=0):
            if depth > self.max_depth:
                span.set_attribute(f"{prefix}", "[DEPTH_EXCEEDED]")
                return

            if isinstance(value, BaseModel):
                value = value.model_dump()

            if isinstance(value, dict):
                for k, v in value.items():
                    _flatten_and_set(span, f"{prefix}.{k}", v, depth + 1)
            elif isinstance(value, list | tuple):
                for idx, item in enumerate(value):
                    _flatten_and_set(span, f"{prefix}[{idx}]", item, depth + 1)
            else:
                try:
                    if any(key in prefix for key in self.redact_keys):
                        span.set_attribute(prefix, "[REDACTED]")
                    else:
                        val = value if isinstance(value, str | int | float | bool) else str(value)
                        if isinstance(val, str) and len(val) > self.max_length:
                            val = val[:self.max_length] + "..."
                        span.set_attribute(prefix, val)
                except Exception:
                    pass

        def _set_span_attributes(span, args, kwargs):
            span.set_attribute("function.name", func.__name__)
            span.set_attribute("function.module", func.__module__)
            span.set_attribute("function.file", func.__code__.co_filename)
            span.set_attribute("function.line", func.__code__.co_firstlineno)

            if self.include_args:
                try:
                    span.set_attribute("function.args", str(args))
                except Exception:
                    pass

                for key, value in kwargs.items():
                    _flatten_and_set(span, f"function.kwargs.{key}", value)

        async def async_wrapper(*args, **kwargs):
            with self.tracer.start_as_current_span(self.name or f"{func.__module__}.{func.__name__}") as span:
                try:
                    _set_span_attributes(span, args, kwargs)
                    return await func(*args, **kwargs)
                except Exception as e:
                    span.record_exception(
                        e,
                        {
                            "exception.code": getattr(e, "error_code", "INTERNAL_SERVER_ERROR"),
                            "exception.type": type(e).__name__,
                            "exception.message": getattr(e, "message", "")
                        }
                    )
                    span.set_status(StatusCode.ERROR)
                    raise

        def sync_wrapper(*args, **kwargs):
            with self.tracer.start_as_current_span(self.name or f"{func.__module__}.{func.__name__}") as span:
                try:
                    _set_span_attributes(span, args, kwargs)
                    return func(*args, **kwargs)
                except Exception as e:
                    span.record_exception(
                        e,
                        {
                            "exception.code": getattr(e, "error_code", "INTERNAL_SERVER_ERROR"),
                            "exception.type": type(e).__name__,
                            "exception.message": getattr(e, "message", "")
                        }
                    )
                    span.set_status(StatusCode.ERROR)
                    raise

        wrapper = async_wrapper if is_async else sync_wrapper
        return update_wrapper(wrapper, func)
