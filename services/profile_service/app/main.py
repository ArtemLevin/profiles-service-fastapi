"""FastAPI application for the profile service."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api import RateLimitExceeded, SlowAPIMiddleware, limiter, profile_router
from .core import DomainError, configure_logging
from .settings import settings
from services.common.observability.middleware import (
    RequestContextMiddleware,
    register_exception_handlers,
)
from services.common.observability.metrics import setup_metrics
from services.common.observability.tracing import configure_tracing, init_sentry, instrument_app
from services.common.observability.utils import parse_csv
from services.common.security import RateLimitMiddleware, SlidingWindowRateLimiter

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.app.log_level)
    if settings.app.tracing_enabled:
        configure_tracing(
            service_name="profile_service",
            exporter_endpoint=settings.app.otlp_endpoint,
            insecure=settings.app.otlp_insecure,
            sample_ratio=settings.app.traces_sample_ratio,
        )
    if settings.app.sentry_dsn:
        init_sentry(
            settings.app.sentry_dsn,
            environment=settings.app.sentry_environment,
            traces_sample_rate=settings.app.sentry_traces_sample_rate,
        )
    if settings.app.tracing_enabled:
        instrument_app(app)
    redis = Redis.from_url(settings.redis.dsn, encoding="utf-8", decode_responses=True)
    app.state.redis = redis
    app.state.limiter = limiter
    logger.info("Profile service startup complete")
    try:
        yield
    finally:
        await redis.close()
        logger.info("Profile service shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Profile Service",
        docs_url="/api/profile/openapi",
        openapi_url="/api/profile/openapi.json",
        lifespan=lifespan,
    )

    register_exception_handlers(app, logger)

    request_headers = parse_csv(settings.app.request_log_headers)
    app.add_middleware(
        RequestContextMiddleware,
        logger=logger,
        request_id_header=settings.app.request_id_header.lower(),
        trust_request_id_header=settings.app.trust_request_id_header,
        log_headers=request_headers,
    )

    allowed_hosts = parse_csv(settings.app.allowed_hosts)
    if allowed_hosts and allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    cors_origins = parse_csv(settings.app.cors_allow_origins) or ["*"]
    cors_methods = parse_csv(settings.app.cors_allow_methods) or ["*"]
    cors_headers = parse_csv(settings.app.cors_allow_headers) or ["*"]
    allow_credentials = settings.app.cors_allow_credentials
    if cors_origins == ["*"] and allow_credentials:
        allow_credentials = False
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=cors_methods,
        allow_headers=cors_headers,
    )

    if settings.rate_limit.enabled:
        exempt_paths = parse_csv(settings.rate_limit.exempt_paths)
        limiter_middleware = SlidingWindowRateLimiter(
            limit=settings.rate_limit.requests,
            interval_seconds=settings.rate_limit.window_seconds,
        )
        app.add_middleware(
            RateLimitMiddleware,
            limiter=limiter_middleware,
            exempt_paths=(*exempt_paths, settings.app.metrics_endpoint),

        )

    app.add_middleware(SlowAPIMiddleware)
    app.include_router(profile_router)

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(_: Request, __: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        payload = exc.payload or {"detail": exc.message}
        if "detail" not in payload:
            payload["detail"] = exc.message
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "OK"}


    if settings.app.metrics_enabled:
        setup_metrics(app, endpoint=settings.app.metrics_endpoint)
    return app


app = create_app()
