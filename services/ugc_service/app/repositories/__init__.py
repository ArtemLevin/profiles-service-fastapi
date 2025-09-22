"""Repository layer exports for the UGC service."""

from .events import EventRepository
from .in_memory import InMemoryEventRepository

__all__ = ["EventRepository", "InMemoryEventRepository"]
