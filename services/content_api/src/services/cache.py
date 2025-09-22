from __future__ import annotations

import logging
from typing import Any, TypeVar

import orjson
from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

LOGGER = logging.getLogger("content_api.cache")

ModelT = TypeVar("ModelT", bound=BaseModel)


class RedisJSONCache:
    """A lightweight JSON cache facade backed by Redis."""

    def __init__(self, client: Redis, *, namespace: str, default_ttl: int) -> None:
        self._client = client
        self._namespace = namespace.rstrip(":")
        self._default_ttl = default_ttl

    def _key(self, key: str) -> str:
        return f"{self._namespace}:{key}" if self._namespace else key

    async def fetch_model(self, key: str, model_type: type[ModelT]) -> ModelT | None:
        raw = await self._get_raw(key)
        if raw is None:
            return None
        try:
            payload = orjson.loads(raw)
            return model_type.model_validate(payload)
        except (orjson.JSONDecodeError, ValidationError) as exc:
            LOGGER.warning("Discarding invalid cache entry", extra={"key": key}, exc_info=exc)
            await self.invalidate(key)
            return None

    async def store_model(self, key: str, model: ModelT, *, ttl: int | None = None) -> None:
        payload = model.model_dump(mode="json")
        await self._set_json(key, payload, ttl=ttl)

    async def _get_raw(self, key: str) -> bytes | None:
        redis_key = self._key(key)
        try:
            return await self._client.get(redis_key)
        except RedisError as exc:  # pragma: no cover - network failure path
            LOGGER.warning("Failed to fetch cache entry", extra={"key": redis_key}, exc_info=exc)
            return None

    async def _set_json(self, key: str, payload: Any, *, ttl: int | None = None) -> None:
        redis_key = self._key(key)
        try:
            await self._client.set(redis_key, orjson.dumps(payload), ex=ttl or self._default_ttl)
        except RedisError as exc:  # pragma: no cover - network failure path
            LOGGER.warning("Failed to write cache entry", extra={"key": redis_key}, exc_info=exc)

    async def invalidate(self, key: str) -> None:
        redis_key = self._key(key)
        try:
            await self._client.delete(redis_key)
        except RedisError as exc:  # pragma: no cover - best effort cleanup
            LOGGER.debug("Failed to invalidate cache entry", extra={"key": redis_key}, exc_info=exc)
