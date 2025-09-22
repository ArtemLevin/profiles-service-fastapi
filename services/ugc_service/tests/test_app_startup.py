from contextlib import asynccontextmanager
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from services.ugc_service.app.core.settings import Settings
from services.ugc_service.app.main import create_app

pytestmark = pytest.mark.anyio("asyncio")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@asynccontextmanager
async def lifespan_client(app: Any):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


async def test_app_uses_in_memory_backend_when_clickhouse_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(_: object) -> None:
        raise RuntimeError("clickhouse unreachable")

    monkeypatch.setattr("services.ugc_service.app.main.create_clickhouse_client", _raise)

    settings = Settings(ensure_schema=False, metrics_enabled=False)
    app = create_app(settings=settings)

    async with lifespan_client(app) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "DEGRADED", "backend": "memory"}
