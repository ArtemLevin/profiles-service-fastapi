from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api import api_router
from .core.exceptions import AuthServiceError
from .core.logging import configure_logging
from .db import init_models
from .settings import get_settings
from services.common.observability.middleware import (
    RequestContextMiddleware,
    register_exception_handlers,
)
from services.common.observability.metrics import setup_metrics
from services.common.observability.tracing import configure_tracing, init_sentry, instrument_app
from services.common.observability.utils import parse_csv
from services.common.security import RateLimitMiddleware, SlidingWindowRateLimiter

logger = logging.getLogger("auth_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.app.log_level)
    if settings.app.tracing_enabled:
        configure_tracing(
            service_name="auth_service",
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
    logger.info("Starting auth service")
    await init_models()
    try:
        yield
    finally:
        logger.info("Stopping auth service")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Auth Service",
        docs_url="/api/auth/openapi",
        openapi_url="/api/auth/openapi.json",
        lifespan=lifespan,
    )

    register_exception_handlers(application, logger)

    request_headers = parse_csv(settings.app.request_log_headers)
    application.add_middleware(
        RequestContextMiddleware,
        logger=logger,
        request_id_header=settings.app.request_id_header.lower(),
        trust_request_id_header=settings.app.trust_request_id_header,
        log_headers=request_headers,
    )

    allowed_hosts = parse_csv(settings.app.allowed_hosts)
    if allowed_hosts and allowed_hosts != ["*"]:
        application.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    cors_origins = parse_csv(settings.app.cors_allow_origins) or ["*"]
    cors_methods = parse_csv(settings.app.cors_allow_methods) or ["*"]
    cors_headers = parse_csv(settings.app.cors_allow_headers) or ["*"]
    allow_credentials = settings.app.cors_allow_credentials
    if cors_origins == ["*"] and allow_credentials:
        allow_credentials = False
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=cors_methods,
        allow_headers=cors_headers,
    )


    if settings.rate_limit.enabled:
        exempt_paths = parse_csv(settings.rate_limit.exempt_paths)
        limiter = SlidingWindowRateLimiter(
            limit=settings.rate_limit.requests,
            interval_seconds=settings.rate_limit.window_seconds,

        )
        application.add_middleware(
            RateLimitMiddleware,
            limiter=limiter,
            exempt_paths=(*exempt_paths, settings.app.metrics_endpoint),
        )

    if settings.app.metrics_enabled:
        setup_metrics(application, endpoint=settings.app.metrics_endpoint)


    @application.exception_handler(AuthServiceError)
    async def auth_service_error_handler(request: Request, exc: AuthServiceError) -> JSONResponse:
        logger.warning(
            "Domain error",
            extra={"detail": exc.detail, "status_code": exc.status_code, "path": request.url.path},
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "OK"}

    application.include_router(api_router)
    return application


app = create_app()
