import pytest
from uuid import uuid4

# Границы и шаги для рейтинга
valid_ratings = [0, 0.5, 5, 9.5, 10]
invalid_ratings = [-0.5, 10.5, 1.1, 7.3, 11]


@pytest.mark.parametrize("rating", valid_ratings)
async def test_rating_validation_valid(client, bearer_token, rating):
    film_id = str(uuid4())
    r = await client.put(
        f"/api/profile/me/ratings?film_id={film_id}",
        json={"film_id": film_id, "rating": rating},
        headers={"Authorization": bearer_token},
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data["rating"] == float(rating)


@pytest.mark.parametrize("rating", invalid_ratings)
async def test_rating_validation_invalid(client, bearer_token, rating):
    film_id = str(uuid4())
    r = await client.put(
        f"/api/profile/me/ratings?film_id={film_id}",
        json={"film_id": film_id, "rating": rating},
        headers={"Authorization": bearer_token},
    )
    assert r.status_code == 422, r.text


async def test_rating_update(client, bearer_token):
    film_id = str(uuid4())
    # Сначала ставим рейтинг 5
    r = await client.put(
        f"/api/profile/me/ratings?film_id={film_id}",
        json={"film_id": film_id, "rating": 5},
        headers={"Authorization": bearer_token},
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data["rating"] == 5.0
    # Обновляем на 7.5
    r = await client.put(
        f"/api/profile/me/ratings?film_id={film_id}",
        json={"film_id": film_id, "rating": 7.5},
        headers={"Authorization": bearer_token},
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data["rating"] == 7.5
    # Проверяем get
    r = await client.get(
        f"/api/profile/me/ratings?film_id={film_id}", headers={"Authorization": bearer_token}
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["rating"] == 7.5
