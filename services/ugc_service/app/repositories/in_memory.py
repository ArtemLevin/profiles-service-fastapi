"""In-memory fallback repository for UGC events."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Deque

from ..schemas import UserEventCreate, UserEventRead


class InMemoryEventRepository:
    """Store user events in memory when ClickHouse is unavailable."""

    def __init__(self, *, max_events: int | None = 1000) -> None:
        # ``deque`` keeps the most recent events while bounding memory usage.
        self._events: Deque[UserEventRead] = deque(maxlen=max_events)

    async def ensure_schema(self) -> None:  # pragma: no cover - no-op
        """Mirror the ClickHouse repository API."""

        return None

    async def insert_event(self, event: UserEventCreate) -> None:
        """Append a copy of the created event to the in-memory store."""

        payload = deepcopy(event.payload) if event.payload is not None else None
        stored = UserEventRead(
            user_id=event.user_id,
            movie_id=event.movie_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            payload=payload,
        )
        self._events.append(stored)

    async def fetch_recent(self, limit: int) -> list[UserEventRead]:
        """Return the most recent events in reverse chronological order."""

        if limit <= 0:
            return []
        items = list(self._events)
        # ``deque`` stores events from oldest→newest so we reverse and slice.
        return list(reversed(items))[:limit]


__all__ = ["InMemoryEventRepository"]
