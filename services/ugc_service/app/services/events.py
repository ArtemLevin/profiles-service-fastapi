"""Business logic for working with user events."""

from __future__ import annotations

import logging

from typing import Protocol

from ..core.exceptions import EventPersistenceError, EventQueryError, RepositoryError
from ..schemas import UserEventCreate, UserEventRead

LOGGER = logging.getLogger(__name__)


class EventRepositoryProtocol(Protocol):
    async def ensure_schema(self) -> None: ...

    async def insert_event(self, event: UserEventCreate) -> None: ...

    async def fetch_recent(self, limit: int) -> list[UserEventRead]: ...


class EventServiceProtocol(Protocol):
    async def ensure_schema(self) -> None: ...

    async def record_event(self, event: UserEventCreate) -> None: ...

    async def list_events(self, limit: int) -> list[UserEventRead]: ...


class EventService(EventServiceProtocol):
    """Coordinate persistence and retrieval of user-generated content events."""

    def __init__(self, repository: EventRepositoryProtocol) -> None:
        self._repository = repository

    async def ensure_schema(self) -> None:
        """Ensure the ClickHouse tables exist."""

        await self._repository.ensure_schema()

    async def record_event(self, event: UserEventCreate) -> None:
        """Store a new event in ClickHouse."""

        try:
            await self._repository.insert_event(event)
        except RepositoryError as exc:
            LOGGER.exception(
                "Failed to persist user event",
                extra={"event_type": event.event_type, "user_id": event.user_id},
            )
            raise EventPersistenceError("Failed to persist event") from exc

    async def list_events(self, limit: int) -> list[UserEventRead]:
        """Return the most recent events up to the provided limit."""

        try:
            return await self._repository.fetch_recent(limit=limit)
        except RepositoryError as exc:
            LOGGER.exception("Failed to load recent events", extra={"limit": limit})
            raise EventQueryError("Failed to load events") from exc
