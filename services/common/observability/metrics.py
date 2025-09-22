"""Prometheus instrumentation helpers for FastAPI services."""

from __future__ import annotations

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator, metrics


def setup_metrics(app: FastAPI, endpoint: str = "/metrics") -> Instrumentator:
    """Register Prometheus metrics endpoint and standard collectors."""

    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=False,
        should_instrument_requests_inprogress=True,
    )
    instrumentator.add(metrics.request_processing_time())
    instrumentator.add(metrics.request_size())
    instrumentator.add(metrics.response_size())
    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint=endpoint, tags=["metrics"], include_in_schema=False)
    app.state.metrics = instrumentator
    return instrumentator


__all__ = ["setup_metrics"]
