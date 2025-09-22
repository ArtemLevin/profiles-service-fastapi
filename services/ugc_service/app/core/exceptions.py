"""Domain-specific exceptions and exception handlers for the UGC service."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class ServiceError(Exception):
    """Base error for service-level failures."""

    def __init__(
        self, message: str, *, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class RepositoryError(ServiceError):
    """Raised when ClickHouse operations fail."""


class EventPersistenceError(ServiceError):
    """Raised when the service cannot store an incoming event."""


class EventQueryError(ServiceError):
    """Raised when fetching events from the data store fails."""


def register_exception_handlers(app: FastAPI) -> None:
    """Attach JSON error handlers for domain-specific exceptions."""

    @app.exception_handler(ServiceError)
    async def handle_service_error(
        request: Request, exc: ServiceError
    ) -> JSONResponse:  # pragma: no cover - FastAPI glue
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
