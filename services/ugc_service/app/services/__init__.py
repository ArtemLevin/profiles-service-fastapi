"""Service layer exports for the UGC service."""

from .events import EventRepositoryProtocol, EventService, EventServiceProtocol

__all__ = ["EventService", "EventServiceProtocol", "EventRepositoryProtocol"]

