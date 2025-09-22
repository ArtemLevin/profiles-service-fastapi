from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .api.v1 import films, genres, persons
from .core.config import get_settings
from .core.exceptions import register_exception_handlers as register_content_exception_handlers
from .core.logging import configure_logging
from .db.elastic import close_elastic, create_elastic_client, ping_elastic
from .db.redis_client import close_redis, create_redis_client, get_redis_from_state, ping_redis
from .services.cache import RedisJSONCache
from .services.container import build_service_container
from services.common.observability.middleware import (
    RequestContextMiddleware,
    register_exception_handlers,
)
from services.common.observability.metrics import setup_metrics
from services.common.observability.tracing import configure_tracing, init_sentry, instrument_app
from services.common.observability.utils import parse_csv
from services.common.security import RateLimitMiddleware, SlidingWindowRateLimiter

LOGGER = logging.getLogger("content_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.tracing_enabled:
        configure_tracing(
            service_name="content_api",
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
    if settings.tracing_enabled:
        instrument_app(app)

    redis = await create_redis_client(settings)
    elastic = create_elastic_client(settings)
    cache = RedisJSONCache(
        redis, namespace=settings.cache_namespace, default_ttl=settings.redis_cache_ttl_seconds
    )
    services = build_service_container(elastic=elastic, cache=cache, settings=settings)

    app.state.redis = redis
    app.state.elastic = elastic
    app.state.cache = cache
    app.state.services = services

    await ping_redis(redis)
    await ping_elastic(elastic)

    try:
        yield
    finally:
        await close_redis(redis)
        await close_elastic(elastic)


settings = get_settings()
app = FastAPI(
    title=settings.project_name,
    docs_url="/api/content/openapi",
    openapi_url="/api/content/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

register_exception_handlers(app, LOGGER)
register_content_exception_handlers(app)

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

app.include_router(films.router, prefix="/api/content/films", tags=["films"])
app.include_router(genres.router, prefix="/api/content/genres", tags=["genres"])
app.include_router(persons.router, prefix="/api/content/persons", tags=["persons"])


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Lightweight health endpoint for gateway monitoring."""

    redis = get_redis_from_state(app.state)
    status = "OK"
    try:
        await redis.ping()
    except Exception:  # pragma: no cover - health degraded path
        LOGGER.warning("Redis health check failed", exc_info=True)
        status = "DEGRADED"
    return {"status": status}
