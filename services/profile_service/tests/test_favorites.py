import pytest
from httpx import AsyncClient
from uuid import uuid4

import asyncio

pytestmark = pytest.mark.asyncio

FAVORITES_URL = "/api/profile/me/favorites"

async def create_profile(client):
    resp = await client.post("/api/profile", json={
        "full_name": "Test User",
        "phone": "+79999999999",
        "marketing_opt_in": False
    })
    assert resp.status_code == 201
    return resp.json()

async def auth_client(ac: AsyncClient):
    # monkeypatch: always return user_id=1
    ac.headers["Authorization"] = "Bearer testtoken"
    return ac

@pytest.fixture
def film_ids():
    return [str(uuid4()) for _ in range(5)]

async def test_favorites_idempotency_and_delete(async_client, film_ids):
    client = await auth_client(async_client)
    await create_profile(client)
    film_id = film_ids[0]
    # Add favorite twice
    resp1 = await client.post(FAVORITES_URL, json={"film_id": film_id})
    resp2 = await client.post(FAVORITES_URL, json={"film_id": film_id})
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json() == resp2.json()
    # Delete favorite twice
    resp3 = await client.delete(FAVORITES_URL, json={"film_id": film_id})
    assert resp3.status_code == 204
    resp4 = await client.delete(FAVORITES_URL, json={"film_id": film_id})
    assert resp4.status_code == 204

async def test_favorites_pagination(async_client, film_ids):
    client = await auth_client(async_client)
    await create_profile(client)
    # Add all films to favorites
    for fid in film_ids:
        await client.post(FAVORITES_URL, json={"film_id": fid})
    # Get first 2
    resp = await client.get(FAVORITES_URL + "?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == len(film_ids)
    assert len(data["items"]) == 2
    # Get next 2
    resp2 = await client.get(FAVORITES_URL + "?limit=2&offset=2")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 2
    # Get last
    resp3 = await client.get(FAVORITES_URL + f"?limit=2&offset=4")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert len(data3["items"]) == 1
