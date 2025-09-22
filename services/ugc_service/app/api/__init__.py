"""API layer exports for the UGC service."""

from .dependencies import get_app_settings, get_event_service
from .routes.events import router as events_router

__all__ = [
    "events_router",
    "get_app_settings",
    "get_event_service",
]
