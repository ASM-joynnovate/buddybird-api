import logging
import re

from opentelemetry._logs import SeverityNumber, get_logger_provider

LOG_LEVEL_TO_SEVERITY_NUMBER = {
    logging.CRITICAL: SeverityNumber.FATAL,
    logging.ERROR: SeverityNumber.ERROR,
    logging.WARNING: SeverityNumber.WARN,
    logging.INFO: SeverityNumber.INFO,
    logging.DEBUG: SeverityNumber.DEBUG,
    logging.NOTSET: SeverityNumber.UNSPECIFIED,
}

SENSITIVE_FIELDS = [
    re.compile(r"(password\s*[=:]\s*)[^&\s]+", re.IGNORECASE),
    re.compile(r"(token\s*[=:]\s*)[^&\s]+", re.IGNORECASE),
    re.compile(r"(authorization\s*[=:]\s*)[^&\s]+", re.IGNORECASE),
    re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),  # 그룹 없음
]


def sanitize_message(message: str) -> str:
    sanitized = message
    for pattern in SENSITIVE_FIELDS:
        # 비밀번호 형식 예시: password=
        if pattern.groups:  # noqa: SIM108
            sanitized = pattern.sub(r"\1***", sanitized)
        else:  # 예: 이메일
            sanitized = pattern.sub("***", sanitized)
    return sanitized


class OTELLogHandler(logging.Handler):
    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self.otel_logger = get_logger_provider().get_logger(__name__)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
            sanitized_message = sanitize_message(message)

            severity_number = LOG_LEVEL_TO_SEVERITY_NUMBER.get(record.levelno, SeverityNumber.UNSPECIFIED)

            extra_data = record.__dict__.get("extra_info", {})
            self.otel_logger.emit(
                timestamp=int(record.created * 1e9),
                severity_text=record.levelname,
                severity_number=severity_number,
                body=sanitized_message,
                attributes={
                    "logger.name": record.name,
                    "file.name": record.pathname,
                    "line.number": record.lineno,
                    "function.name": record.funcName,
                    "thread.name": record.threadName,
                    **extra_data,
                },
            )
        except Exception:
            self.handleError(record)
