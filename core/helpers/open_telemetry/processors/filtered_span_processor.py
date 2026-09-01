import re
from typing import ClassVar

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class FilteredSpanProcessor(BatchSpanProcessor):
    EXCLUDED_SPAN_NAMES: ClassVar[list[str]] = ["PING"]
    EXCLUDED_URLS: ClassVar[list[str]] = []

    def on_end(self, span: ReadableSpan) -> None:
        for regex in self.EXCLUDED_SPAN_NAMES:
            if re.match(regex, span.name):
                return
        if "http.url" in span.attributes:
            for regex in self.EXCLUDED_URLS:
                if re.match(regex, span.attributes["http.url"]):
                    return
        super().on_end(span)
