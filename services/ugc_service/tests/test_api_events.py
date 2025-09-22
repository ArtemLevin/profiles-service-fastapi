from __future__ import annotations

from datetime import datetime, timezone

from contextlib import asynccontextmanager
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient


from services.ugc_service.app.main import create_app
from services.ugc_service.app.schemas import UserEventCreate, UserEventRead
from services.ugc_service.app.core.settings import Settings

pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class StubEventService:
    def __init__(self, events: list[UserEventRead] | None = None) -> None:
        self.events = events or []
        self.recorded: list[UserEventCreate] = []
        self.requested_limits: list[int] = []
        self.ensure_schema_calls = 0

    async def ensure_schema(self) -> None:  # pragma: no cover - simple counter
        self.ensure_schema_calls += 1

    async def record_event(self, event: UserEventCreate) -> None:
        self.recorded.append(event)

    async def list_events(self, limit: int) -> list[UserEventRead]:
        self.requested_limits.append(limit)
        return list(self.events)


def _sample_read_event() -> UserEventRead:
    return UserEventRead(
        user_id="1",
        movie_id="2",
        event_type="like",
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        payload={"action": "like"},
    )


@asynccontextmanager
async def lifespan_client(app: Any):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


async def test_create_event_endpoint_records_event() -> None:
    service = StubEventService()
    settings = Settings(default_list_limit=10, max_list_limit=50, ensure_schema=False)
    app = create_app(settings=settings, event_service=service)

    async with lifespan_client(app) as client:

        response = await client.post(
            "/api/ugc/events",
            json={"user_id": "1", "movie_id": "2", "event_type": "view"},
        )

    assert response.status_code == 200, response.text
    assert service.recorded[0].event_type == "view"


async def test_legacy_event_endpoint_still_supported() -> None:
    service = StubEventService()
    settings = Settings(default_list_limit=5, max_list_limit=50, ensure_schema=False)
    app = create_app(settings=settings, event_service=service)


    async with lifespan_client(app) as client:

        response = await client.post(
            "/api/ugc/event",
            json={"user_id": "1", "movie_id": "2", "event_type": "view"},
        )

    assert response.status_code == 200
    assert service.recorded[0].movie_id == "2"


async def test_list_events_enforces_limit_and_returns_payload() -> None:
    service = StubEventService(events=[_sample_read_event()])
    settings = Settings(default_list_limit=2, max_list_limit=10, ensure_schema=False)
    app = create_app(settings=settings, event_service=service)

    async with lifespan_client(app) as client:

        response = await client.get("/api/ugc/events", params={"limit": 20})

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 10
    assert data["items"][0]["payload"] == {"action": "like"}
    assert service.requested_limits == [10]


async def test_list_events_uses_default_limit() -> None:
    service = StubEventService(events=[_sample_read_event()])
    settings = Settings(default_list_limit=3, max_list_limit=5, ensure_schema=False)
    app = create_app(settings=settings, event_service=service)

    async with lifespan_client(app) as client:

        response = await client.get("/api/ugc/events")

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 3
    assert service.requested_limits == [3]


async def test_health_endpoint_reports_ok_without_client() -> None:
    service = StubEventService()
    settings = Settings(ensure_schema=False)
    app = create_app(settings=settings, event_service=service)

    async with lifespan_client(app) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "OK", "backend": "custom"}

