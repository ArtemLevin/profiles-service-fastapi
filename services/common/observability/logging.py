"""Structured logging helpers shared by backend services."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any, Final

try:  # pragma: no cover - optional tracing dependency
    from opentelemetry import trace as trace_api
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    trace_api = None


_REQUEST_ID: Final[ContextVar[str | None]] = ContextVar("request_id", default=None)


def bind_request_id(request_id: str) -> Token[str | None]:
    """Store the request identifier in the current context."""

    return _REQUEST_ID.set(request_id)


def release_request_id(token: Token[str | None]) -> None:
    """Reset the request identifier context variable."""

    _REQUEST_ID.reset(token)


def get_request_id() -> str | None:
    """Return the currently bound request identifier."""

    return _REQUEST_ID.get()


def _get_trace_id() -> str | None:
    """Return the trace id from OpenTelemetry, if available."""

    if trace_api is None:  # pragma: no cover - optional dependency
        return None
    span = trace_api.get_current_span()
    if span is None:  # pragma: no cover - defensive
        return None
    context = span.get_span_context()
    if context.trace_id == 0:
        return None
    return f"{context.trace_id:032x}"


class RequestContextFilter(logging.Filter):
    """Inject request and trace identifiers into log records."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - thin wrapper
        record.service = self.service_name
        record.request_id = get_request_id()
        record.trace_id = _get_trace_id()
        return True


class JsonFormatter(logging.Formatter):
    """Format log records as JSON payloads suitable for aggregation."""

    RESERVED = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": getattr(record, "service", None),
            "request_id": getattr(record, "request_id", None),
            "trace_id": getattr(record, "trace_id", None),
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = record.stack_info

        for key, value in record.__dict__.items():
            if key in self.RESERVED or key.startswith("_"):
                continue
            payload.setdefault(key, value)

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(service_name: str, level: str) -> logging.Logger:
    """Configure structured logging and return the service logger."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestContextFilter(service_name))

    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)
    logger = logging.getLogger(service_name)
    logger.setLevel(level.upper())
    logger.debug("Logging configured", extra={"level": level})
    return logger


__all__ = [
    "JsonFormatter",
    "RequestContextFilter",
    "bind_request_id",
    "configure_logging",
    "get_request_id",
    "release_request_id",
]
