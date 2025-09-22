from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class RateLimitExceeded(Exception):
    """Placeholder exception to mirror slowapi's behaviour."""


def get_remote_address(_: Any) -> str:
    return "anonymous"


@dataclass
class _LimiterState:
    limits: dict[Callable[..., Any], str]


class Limiter:
    def __init__(
        self, key_func: Callable[[Any], str] | None = None, storage_uri: str | None = None
    ) -> None:  # noqa: D401
        self.key_func = key_func or get_remote_address
        self.storage_uri = storage_uri
        self._state = _LimiterState(limits={})

    def limit(self, limit_value: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._state.limits[func] = limit_value
            return func

        return decorator


class SlowAPIMiddleware:
    """No-op ASGI middleware used when slowapi is unavailable."""

    def __init__(self, app: Callable[..., Any]) -> None:
        self.app = app

    async def __call__(
        self, scope: Any, receive: Callable[..., Any], send: Callable[..., Any]
    ) -> None:
        await self.app(scope, receive, send)
