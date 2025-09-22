from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import pytest

from services.content_api.src.core.exceptions import ContentNotFoundError, ExternalServiceError
from services.content_api.src.models.models import Film
from services.content_api.src.services.content_service import ContentService


@dataclass
class DummyRepository:
    index_name: str
    data: dict[str, dict[str, Any]]
    search_results: list[dict[str, Any]] | None = None
    get_calls: int = 0

    async def get(self, entity_id: str) -> dict[str, Any]:
        self.get_calls += 1
        if entity_id not in self.data:
            raise ContentNotFoundError(entity=self.index_name, entity_id=entity_id)
        return self.data[entity_id]

    async def search_all(self, size: int) -> list[dict[str, Any]]:
        if self.search_results is not None:
            return self.search_results[:size]
        return list(self.data.values())[:size]


class InMemoryCache:
    def __init__(self) -> None:
        self.store: dict[str, Film] = {}

    async def fetch_model(self, key: str, model_type: type[Film]) -> Film | None:
        return self.store.get(key)

    async def store_model(
        self, key: str, model: Film, *, ttl: int | None = None
    ) -> None:  # noqa: ARG002 - ttl kept for parity
        self.store[key] = model


@pytest.mark.anyio("asyncio")
async def test_get_uses_cache_before_repository() -> None:
    entity_id = uuid4()
    cached_film = Film(id=entity_id, title="The Cache", description="cached")
    repo = DummyRepository(
        index_name="films", data={str(entity_id): cached_film.model_dump(mode="json")}
    )
    cache = InMemoryCache()
    cache.store["films:" + str(entity_id)] = cached_film

    service = ContentService(
        repository=repo,
        cache=cache,
        model_type=Film,
        cache_ttl_seconds=60,
        default_page_size=10,
    )

    result = await service.get(entity_id)

    assert result == cached_film
    assert repo.get_calls == 0


@pytest.mark.anyio("asyncio")
async def test_get_populates_cache_on_miss() -> None:
    entity_id = uuid4()
    film_payload = {"id": str(entity_id), "title": "Repository Result"}
    repo = DummyRepository(index_name="films", data={str(entity_id): film_payload})
    cache = InMemoryCache()

    service = ContentService(
        repository=repo,
        cache=cache,
        model_type=Film,
        cache_ttl_seconds=120,
        default_page_size=10,
    )

    result = await service.get(entity_id)

    assert result.title == "Repository Result"
    assert repo.get_calls == 1
    assert cache.store["films:" + str(entity_id)] == result


@pytest.mark.anyio("asyncio")
async def test_get_propagates_not_found() -> None:
    service = ContentService(
        repository=DummyRepository(index_name="films", data={}),
        cache=InMemoryCache(),
        model_type=Film,
        cache_ttl_seconds=60,
        default_page_size=10,
    )

    with pytest.raises(ContentNotFoundError):
        await service.get(uuid4())


@pytest.mark.anyio("asyncio")
async def test_list_validates_payloads() -> None:
    entity_id = uuid4()
    repo = DummyRepository(
        index_name="films",
        data={},
        search_results=[{"id": str(entity_id), "title": "A Film"}],
    )
    cache = InMemoryCache()

    service = ContentService(
        repository=repo,
        cache=cache,
        model_type=Film,
        cache_ttl_seconds=60,
        default_page_size=5,
    )

    items = await service.list(size=1)

    assert len(items) == 1
    assert items[0].id == entity_id


@pytest.mark.anyio("asyncio")
async def test_list_raises_for_invalid_payload() -> None:
    repo = DummyRepository(
        index_name="films",
        data={},
        search_results=[{"id": str(uuid4())}],
    )
    service = ContentService(
        repository=repo,
        cache=InMemoryCache(),
        model_type=Film,
        cache_ttl_seconds=60,
        default_page_size=5,
    )

    with pytest.raises(ExternalServiceError):
        await service.list(size=1)
