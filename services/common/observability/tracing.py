"""OpenTelemetry and Sentry helpers for backend services."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

try:  # pragma: no cover - optional dependency
    from opentelemetry import trace as _trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter as _OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor as _FastAPIInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor as _LoggingInstrumentor
    from opentelemetry.sdk.resources import Resource as _Resource
    from opentelemetry.sdk.trace import TracerProvider as _TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor as _BatchSpanProcessor,
        ConsoleSpanExporter as _ConsoleSpanExporter,
    )
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased as _TraceIdRatioBased
except ModuleNotFoundError:  # pragma: no cover - graceful degradation
    _trace = None
    _FastAPIInstrumentor = None
    _LoggingInstrumentor = None
    _OTLPSpanExporter = None
    _TracerProvider = None
    _BatchSpanProcessor = None
    _ConsoleSpanExporter = None
    _Resource = None
    _TraceIdRatioBased = None

trace: Any = _trace
FastAPIInstrumentor: Any = _FastAPIInstrumentor
LoggingInstrumentor: Any = _LoggingInstrumentor
OTLPSpanExporter: Any = _OTLPSpanExporter
TracerProvider: Any = _TracerProvider
BatchSpanProcessor: Any = _BatchSpanProcessor
ConsoleSpanExporter: Any = _ConsoleSpanExporter
Resource: Any = _Resource
TraceIdRatioBased: Any = _TraceIdRatioBased

try:  # pragma: no cover - optional dependency
    import sentry_sdk as _sentry_sdk
except ModuleNotFoundError:  # pragma: no cover
    _sentry_sdk = None

sentry_sdk: Any = _sentry_sdk


_LOGGER = logging.getLogger("observability.tracing")
_TRACING_CONFIGURED = False


def configure_tracing(
    *,
    service_name: str,
    exporter_endpoint: str | None = None,
    insecure: bool = False,
    sample_ratio: float = 1.0,
) -> None:
    """Configure OpenTelemetry tracing if the dependency is installed."""

    if trace is None or TracerProvider is None or Resource is None:
        _LOGGER.debug("OpenTelemetry not installed; skipping tracing setup")
        return

    global _TRACING_CONFIGURED
    if _TRACING_CONFIGURED:
        return

    sample_ratio = max(0.0, min(sample_ratio, 1.0))
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource, sampler=TraceIdRatioBased(sample_ratio))

    span_exporter: Any
    if exporter_endpoint:
        if OTLPSpanExporter is None:  # pragma: no cover - optional dependency
            _LOGGER.warning(
                "OTLP exporter not available; falling back to console exporter",
                extra={"endpoint": exporter_endpoint},
            )
            span_exporter = ConsoleSpanExporter()
        else:
            span_exporter = OTLPSpanExporter(endpoint=exporter_endpoint, insecure=insecure)
    else:  # pragma: no cover - console fallback
        span_exporter = ConsoleSpanExporter()

    processor = BatchSpanProcessor(span_exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    if LoggingInstrumentor is not None:  # pragma: no cover - optional dependency
        LoggingInstrumentor().instrument(set_logging_format=False)

    _LOGGER.info("Tracing configured", extra={"endpoint": exporter_endpoint})
    _TRACING_CONFIGURED = True


def instrument_app(app: FastAPI) -> None:
    """Instrument FastAPI routes for OpenTelemetry tracing."""

    if FastAPIInstrumentor is None:
        _LOGGER.debug("FastAPI instrumentation not available")
        return
    FastAPIInstrumentor.instrument_app(app)


def init_sentry(
    dsn: str | None,
    *,
    environment: str | None = None,
    release: str | None = None,
    traces_sample_rate: float = 0.0,
) -> None:
    """Initialise Sentry SDK if configured."""

    if not dsn:
        return
    if sentry_sdk is None:  # pragma: no cover - optional dependency
        _LOGGER.warning("sentry-sdk not installed; DSN configured but ignored")
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=max(0.0, min(traces_sample_rate, 1.0)),
    )
    _LOGGER.info("Sentry configured", extra={"environment": environment})


__all__ = ["configure_tracing", "init_sentry", "instrument_app"]
