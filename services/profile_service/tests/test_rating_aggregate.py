import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_rating_aggregate_cache_and_invalidate(client, bearer_token, redis):
    film_id = str(uuid4())
    # 1. Ставим рейтинг 5
    r = await client.put(f"/api/profile/me/ratings?film_id={film_id}", json={"film_id": film_id, "rating": 5}, headers={"Authorization": bearer_token})
    assert r.status_code in (200, 201), r.text
    # 2. Получаем агрегат (должен быть 5, count=1)
    r = await client.get(f"/api/profile/public/films/{film_id}/rating-agg")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["avg_rating"] == 5.0
    assert data["ratings_count"] == 1
    # 3. Меняем рейтинг на 7.5 (инвалидация кэша)
    r = await client.put(f"/api/profile/me/ratings?film_id={film_id}", json={"film_id": film_id, "rating": 7.5}, headers={"Authorization": bearer_token})
    assert r.status_code in (200, 201), r.text
    # 4. Получаем агрегат (должен быть 7.5, count=1)
    r = await client.get(f"/api/profile/public/films/{film_id}/rating-agg")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["avg_rating"] == 7.5
    assert data["ratings_count"] == 1
    # 5. Проверяем, что кэш в Redis есть
    key = f"rating_agg:{film_id}"
    cached = await redis.get(key)
    assert cached is not None
    avg, count = cached.split(":")
    assert float(avg) == 7.5
    assert int(count) == 1
    # 6. Удаляем кэш вручную и убеждаемся, что после следующего запроса он снова появляется
    await redis.delete(key)
    r = await client.get(f"/api/profile/public/films/{film_id}/rating-agg")
    assert r.status_code == 200
    cached = await redis.get(key)
    assert cached is not None
