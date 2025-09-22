from __future__ import annotations

from datetime import datetime

import pytest

from services.ugc_service.app.core.exceptions import (
    EventPersistenceError,
    EventQueryError,
    RepositoryError,
)
from services.ugc_service.app.schemas import UserEventCreate, UserEventRead
from services.ugc_service.app.services.events import EventService

pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class InMemoryRepository:
    def __init__(self) -> None:
        self.inserted: list[UserEventCreate] = []
        self.events: list[UserEventRead] = []
        self.ensure_schema_calls = 0
        self.requested_limits: list[int] = []

    async def ensure_schema(self) -> None:
        self.ensure_schema_calls += 1

    async def insert_event(self, event: UserEventCreate) -> None:
        self.inserted.append(event)

    async def fetch_recent(self, limit: int) -> list[UserEventRead]:
        self.requested_limits.append(limit)
        return list(self.events)


class FailingInsertRepository(InMemoryRepository):
    async def insert_event(
        self, event: UserEventCreate
    ) -> None:  # noqa: D401 - behaviour documented in parent
        raise RepositoryError("down")


class FailingQueryRepository(InMemoryRepository):
    async def fetch_recent(
        self, limit: int
    ) -> list[UserEventRead]:  # noqa: D401 - behaviour documented in parent
        raise RepositoryError("down")


def _sample_event_payload() -> dict[str, str]:
    return {"action": "play"}


@pytest.fixture
def user_event() -> UserEventCreate:
    return UserEventCreate(
        user_id="42",
        movie_id="24",
        event_type="view",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        payload=_sample_event_payload(),
    )


async def test_records_event(user_event: UserEventCreate) -> None:
    repository = InMemoryRepository()
    service = EventService(repository=repository)

    await service.record_event(user_event)

    assert repository.inserted[0].user_id == "42"


async def test_raises_when_repository_fails_to_persist(user_event: UserEventCreate) -> None:
    repository = FailingInsertRepository()
    service = EventService(repository=repository)

    with pytest.raises(EventPersistenceError):
        await service.record_event(user_event)


async def test_lists_events_with_requested_limit() -> None:
    repository = InMemoryRepository()
    event = UserEventRead(
        user_id="1",
        movie_id="2",
        event_type="like",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        payload=_sample_event_payload(),
    )
    repository.events = [event]
    service = EventService(repository=repository)

    items = await service.list_events(limit=5)

    assert items == [event]
    assert repository.requested_limits == [5]


async def test_raises_when_repository_fails_to_query() -> None:
    repository = FailingQueryRepository()
    service = EventService(repository=repository)

    with pytest.raises(EventQueryError):
        await service.list_events(limit=1)
