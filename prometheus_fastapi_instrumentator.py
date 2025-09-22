"""Lightweight fallback stub for prometheus-fastapi-instrumentator."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import FastAPI
from fastapi.responses import JSONResponse


class _DummyMetric:
    def __call__(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - trivial stub
        return None


class metrics:  # pragma: no cover - stub module
    @staticmethod
    def request_processing_time(*args: Any, **kwargs: Any) -> _DummyMetric:
        return _DummyMetric()

    @staticmethod
    def request_size(*args: Any, **kwargs: Any) -> _DummyMetric:
        return _DummyMetric()

    @staticmethod
    def response_size(*args: Any, **kwargs: Any) -> _DummyMetric:
        return _DummyMetric()


class Instrumentator:  # pragma: no cover - stub module
    def __init__(self, **_: Any) -> None:
        self._metrics: list[Any] = []

    def add(self, metric: Callable[..., Any]) -> "Instrumentator":
        self._metrics.append(metric)
        return self

    def instrument(self, app: FastAPI) -> "Instrumentator":
        return self

    def expose(
        self,
        app: FastAPI,
        *,
        endpoint: str = "/metrics",
        tags: list[str] | None = None,
        include_in_schema: bool = False,
    ) -> "Instrumentator":
        async def _metrics() -> JSONResponse:
            return JSONResponse(content={"metrics": "disabled"})

        app.add_api_route(endpoint, _metrics, include_in_schema=include_in_schema, tags=tags or [])
        return self


__all__ = ["Instrumentator", "metrics"]
