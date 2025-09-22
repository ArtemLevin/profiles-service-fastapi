"""Lightweight in-memory rate limiting middleware for ASGI apps."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Awaitable, Callable, Deque, Sequence

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

IdentifierFunc = Callable[[Request], str]


def _default_identifier(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


class SlidingWindowRateLimiter:
    """A simple sliding window limiter suitable for single-process deployments."""

    def __init__(self, *, limit: int, interval_seconds: float) -> None:
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")
        self.limit = limit
        self.interval = interval_seconds
        self._buckets: dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        now = time.monotonic()
        async with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            while bucket and now - bucket[0] > self.interval:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return False
            bucket.append(now)
            return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply rate limiting using a :class:`SlidingWindowRateLimiter` instance."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limiter: SlidingWindowRateLimiter,
        identifier: IdentifierFunc | None = None,
        exempt_paths: Sequence[str] | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(app)
        self.limiter = limiter
        self.identifier = identifier or _default_identifier
        self.exempt_paths = tuple(exempt_paths or ())
        self.retry_after = retry_after or limiter.interval

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if self._is_exempt(request.url.path):
            return await call_next(request)

        key = self.identifier(request)
        allowed = await self.limiter.allow(key)
        if not allowed:
            headers = {"Retry-After": str(int(self.retry_after))}
            return JSONResponse(
                status_code=429, content={"detail": "Too Many Requests"}, headers=headers
            )
        return await call_next(request)

    def _is_exempt(self, path: str) -> bool:
        for prefix in self.exempt_paths:
            if path.startswith(prefix):
                return True
        return False


__all__ = ["RateLimitMiddleware", "SlidingWindowRateLimiter"]
