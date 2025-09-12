import os
from jose import jwt

async def test_conflict_phone_between_users(client, bearer_token):
    r = await client.post("/api/profile", json={
        "full_name": "User1",
        "phone": "+12025550111"
    }, headers={"Authorization": bearer_token})
    assert r.status_code == 201, r.text

    token2 = jwt.encode({"sub": "124"}, os.environ["JWT_SECRET"], algorithm=os.environ["JWT_ALG"])
    r2 = await client.post("/api/profile", json={
        "full_name": "User2",
        "phone": "+1 (202) 555-0111"
    }, headers={"Authorization": f"Bearer {token2}"})
    assert r2.status_code == 409

async def test_invalid_phone(client, bearer_token):
    r = await client.post("/api/profile", json={
        "full_name": "Bad",
        "phone": "12345"
    }, headers={"Authorization": bearer_token})
    assert r.status_code == 422
