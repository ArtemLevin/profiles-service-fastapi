from __future__ import annotations

import logging
from typing import Any

import inspect

from redis.asyncio import Redis
from redis.backoff import ExponentialBackoff
from redis.asyncio.retry import Retry
from redis.exceptions import RedisError

from ..core.settings import Settings

LOGGER = logging.getLogger("content_api.redis")


async def create_redis_client(settings: Settings) -> Redis:
    """Create a configured Redis client instance."""

    retry = Retry(
        ExponentialBackoff(cap=settings.redis_retry_backoff_seconds),
        retries=settings.redis_retry_attempts,
    )
    client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password,
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        retry=retry,
        decode_responses=False,
        health_check_interval=30,
    )
    return client


async def ping_redis(client: Redis) -> bool:
    """Ping redis and log failures without raising."""

    try:
        await client.ping()
        return True
    except RedisError as exc:  # pragma: no cover - network failure path
        LOGGER.warning("Redis ping failed", exc_info=exc)
        return False


async def close_redis(client: Redis) -> None:
    """Gracefully close the Redis client."""

    try:
        await client.close()
    except (RedisError, AttributeError):  # pragma: no cover - close best effort
        LOGGER.exception("Failed to close redis client")
    pool = getattr(client, "connection_pool", None)
    if pool is None:
        return
    disconnect = getattr(pool, "disconnect", None)
    if callable(disconnect):
        try:
            result = disconnect()
            if inspect.isawaitable(result):
                await result
        except (RedisError, AttributeError):  # pragma: no cover - best effort cleanup
            LOGGER.debug("Redis connection pool already closed")


class RedisUnavailableError(RuntimeError):
    """Raised when a Redis dependency is missing from application state."""


def get_redis_from_state(state: Any) -> Redis:
    client = getattr(state, "redis", None)
    if client is None:
        raise RedisUnavailableError("Redis client has not been initialised")
    return client
