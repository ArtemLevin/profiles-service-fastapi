from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse

LOGGER = logging.getLogger("content_api.exceptions")


@dataclass(slots=True)
class ContentServiceError(Exception):
    """Base class for domain-specific exceptions."""

    message: str = ""

    def __str__(self) -> str:  # pragma: no cover - dataclass str override
        return self.message


@dataclass(slots=True)
class ContentNotFoundError(ContentServiceError):
    """Raised when the requested document cannot be located."""

    entity: str = ""
    entity_id: str = ""

    def __post_init__(self) -> None:
        if not self.entity or not self.entity_id:
            raise ValueError("ContentNotFoundError requires both entity and entity_id")
        if not self.message:
            object.__setattr__(self, "message", f"{self.entity} {self.entity_id} not found")


@dataclass(slots=True)
class ExternalServiceError(ContentServiceError):
    """Raised when upstream dependencies fail."""

    details: dict[str, Any] | None = None


def register_exception_handlers(app: FastAPI) -> None:
    """Attach application-wide exception handlers."""

    @app.exception_handler(ContentNotFoundError)
    async def _handle_not_found(request: Request, exc: ContentNotFoundError) -> ORJSONResponse:
        LOGGER.info(
            "Resource not found",
            extra={"entity": exc.entity, "entity_id": exc.entity_id, "path": request.url.path},
        )
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content={"detail": exc.message}
        )

    @app.exception_handler(ExternalServiceError)
    async def _handle_external(request: Request, exc: ExternalServiceError) -> ORJSONResponse:
        LOGGER.error(
            "External dependency failure",
            extra={"path": request.url.path, "details": exc.details},
        )
        return ORJSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": exc.message or "Upstream service failed"},
        )

    @app.exception_handler(ContentServiceError)
    async def _handle_generic(request: Request, exc: ContentServiceError) -> ORJSONResponse:
        LOGGER.error(
            "Unhandled content service error",
            extra={"path": request.url.path, "message": exc.message},
        )
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": exc.message}
        )
