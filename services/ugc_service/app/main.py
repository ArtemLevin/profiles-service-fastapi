"""FastAPI application entrypoint for the UGC service."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api import events_router
from .core.exceptions import register_exception_handlers as register_ugc_exception_handlers
from .core.logging import configure_logging
from .core.settings import Settings, get_settings
from .db.clickhouse import close_clickhouse_client, create_clickhouse_client, ping_clickhouse
from .repositories import EventRepository, InMemoryEventRepository
from .services import EventRepositoryProtocol, EventService, EventServiceProtocol

from services.common.observability.middleware import (
    RequestContextMiddleware,
    register_exception_handlers,
)
from services.common.observability.metrics import setup_metrics
from services.common.observability.tracing import configure_tracing, init_sentry, instrument_app
from services.common.observability.utils import parse_csv
from services.common.security import RateLimitMiddleware, SlidingWindowRateLimiter

LOGGER = logging.getLogger("ugc_service")


def create_app(
    settings: Settings | None = None,
    *,
    event_service: EventServiceProtocol | None = None,
) -> FastAPI:
    """Build and configure the FastAPI application instance."""

    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level)
        if settings.tracing_enabled:
            configure_tracing(
                service_name="ugc_service",
                exporter_endpoint=settings.otlp_endpoint,
                insecure=settings.otlp_insecure,
                sample_ratio=settings.traces_sample_ratio,
            )
        if settings.sentry_dsn:
            init_sentry(
                settings.sentry_dsn,
                environment=settings.sentry_environment,
                traces_sample_rate=settings.sentry_traces_sample_rate,
            )
        app.state.settings = settings
        app.state.event_backend = "unknown"

        if settings.tracing_enabled:
            instrument_app(app)

        if event_service is not None:
            app.state.event_service = event_service
            app.state.event_backend = "custom"

            if hasattr(event_service, "ensure_schema"):
                try:
                    await event_service.ensure_schema()
                except Exception:  # pragma: no cover - defensive logging
                    LOGGER.exception("Custom EventService schema initialisation failed")
            yield
            return

        client: httpx.AsyncClient | None = None
        repository: EventRepositoryProtocol | None = None
        service: EventServiceProtocol

        try:
            client = create_clickhouse_client(settings.clickhouse)
            repository = EventRepository(client=client, database=settings.clickhouse.database)
            service = EventService(repository=repository)

            app.state.clickhouse_client = client
            app.state.event_repository = repository
            app.state.event_service = service
            app.state.event_backend = "clickhouse"

            if settings.ensure_schema:
                await service.ensure_schema()
            await ping_clickhouse(client, settings.clickhouse.database)
        except Exception:
            LOGGER.warning(
                "ClickHouse unavailable; using in-memory fallback",
                exc_info=True,
            )
            if client is not None:
                await close_clickhouse_client(client)
            repository = InMemoryEventRepository()
            service = EventService(repository=repository)
            app.state.clickhouse_client = None
            app.state.event_repository = repository
            app.state.event_service = service
            app.state.event_backend = "memory"
            if settings.ensure_schema:
                await service.ensure_schema()


        try:
            yield
        finally:
            stored_client = getattr(app.state, "clickhouse_client", None)
            if isinstance(stored_client, httpx.AsyncClient):
                await close_clickhouse_client(stored_client)


    app = FastAPI(
        title=settings.service_name,
        docs_url=settings.docs_url,
        openapi_url=settings.openapi_url,
        lifespan=lifespan,
    )
    app.state.settings = settings
    if event_service is not None:
        app.state.event_service = event_service

    register_exception_handlers(app, LOGGER)
    register_ugc_exception_handlers(app)

    request_headers = parse_csv(settings.request_log_headers)
    app.add_middleware(
        RequestContextMiddleware,
        logger=LOGGER,
        request_id_header=settings.request_id_header.lower(),
        trust_request_id_header=settings.trust_request_id_header,
        log_headers=request_headers,
    )

    allowed_hosts = parse_csv(settings.allowed_hosts)
    if allowed_hosts and allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    cors_origins = parse_csv(settings.cors_allow_origins) or ["*"]
    cors_methods = parse_csv(settings.cors_allow_methods) or ["*"]
    cors_headers = parse_csv(settings.cors_allow_headers) or ["*"]
    allow_credentials = settings.cors_allow_credentials
    if cors_origins == ["*"] and allow_credentials:
        allow_credentials = False
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=cors_methods,
        allow_headers=cors_headers,
    )

    if settings.rate_limit_enabled:
        exempt_paths = parse_csv(settings.rate_limit_exempt_paths)
        limiter = SlidingWindowRateLimiter(
            limit=settings.rate_limit_requests,
            interval_seconds=settings.rate_limit_window_seconds,
        )
        app.add_middleware(
            RateLimitMiddleware,
            limiter=limiter,
            exempt_paths=(*exempt_paths, settings.metrics_endpoint),
        )

    if settings.metrics_enabled:
        setup_metrics(app, endpoint=settings.metrics_endpoint)

    app.include_router(events_router, prefix=settings.api_prefix)

    @app.get(settings.health_path, tags=["health"])
    async def health() -> dict[str, str]:  # pragma: no cover - simple proxy
        backend = getattr(app.state, "event_backend", "unknown")
        status_text = "OK"
        if backend == "memory":
            status_text = "DEGRADED"
        else:
            client = getattr(app.state, "clickhouse_client", None)
            if isinstance(client, httpx.AsyncClient):
                try:
                    await ping_clickhouse(client, settings.clickhouse.database)
                except Exception:  # pragma: no cover - health degraded path
                    LOGGER.warning("ClickHouse health probe failed", exc_info=True)
                    status_text = "DEGRADED"
        return {"status": status_text, "backend": backend}


    return app


app = create_app()
