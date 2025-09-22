"""Dependency wiring for the UGC service API."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from ..core.settings import Settings
from ..services.events import EventServiceProtocol


def get_event_service(request: Request) -> EventServiceProtocol:
    """Return the ``EventService`` stored in the application state."""

    service = getattr(request.app.state, "event_service", None)
    if service is None:  # pragma: no cover - defensive programming
        raise RuntimeError("EventService dependency is not configured")
    return cast(EventServiceProtocol, service)


def get_app_settings(request: Request) -> Settings:
    """Return the cached :class:`Settings` instance stored on the app."""

    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):  # pragma: no cover - defensive programming
        raise RuntimeError("Application settings are not configured")
    return settings
