"""ASGI middleware and exception utilities shared across services."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Sequence
from typing import Any, Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from .logging import bind_request_id, release_request_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request metadata and lifecycle logging to each request."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        logger: logging.Logger,
        request_id_header: str = "x-request-id",
        trust_request_id_header: bool = True,
        log_headers: Sequence[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.logger = logger
        self.request_id_header = request_id_header.lower()
        self.trust_request_id_header = trust_request_id_header
        self.log_headers = tuple(header.lower() for header in (log_headers or ()))

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = self._resolve_request_id(request)
        token = bind_request_id(request_id)
        start_time = time.perf_counter()
        client_host = request.client.host if request.client else "unknown"

        extra: dict[str, Any] = {
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_host,
        }
        for header in self.log_headers:
            if header in request.headers:
                extra[f"header_{header}"] = request.headers[header]

        self.logger.debug("Request received", extra=extra)

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            extra["duration_ms"] = round(duration_ms, 3)
            self.logger.exception("Unhandled request error", extra=extra)
            release_request_id(token)
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        extra.update({"status_code": response.status_code, "duration_ms": round(duration_ms, 3)})
        response.headers.setdefault("X-Request-ID", request_id)
        self.logger.info("Request completed", extra=extra)
        release_request_id(token)
        return response

    def _resolve_request_id(self, request: Request) -> str:
        if self.trust_request_id_header:
            header_value = request.headers.get(self.request_id_header)
            if header_value:
                return header_value.strip()
        return uuid.uuid4().hex


def register_exception_handlers(app: FastAPI, logger: logging.Logger) -> None:
    """Install default exception handlers for FastAPI applications."""

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        logger.warning(
            "HTTP error response",
            extra={"status_code": exc.status_code, "path": request.url.path, "detail": exc.detail},
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(
            "Validation failure",
            extra={"path": request.url.path, "errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application exception", extra={"path": request.url.path})
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


__all__ = ["RequestContextMiddleware", "register_exception_handlers"]
