async def test_create_get_update_delete_profile(client, bearer_token):
    r = await client.post("/api/profile", json={
        "full_name": "John Doe",
        "phone": "+1 415 555 2671",
        "marketing_opt_in": True
    }, headers={"Authorization": bearer_token})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["full_name"] == "John Doe"
    assert data["phone"].startswith("+1")
    assert data["marketing_opt_in"] is True
    assert data["user_id"] == 123

    r = await client.get("/api/profile/me", headers={"Authorization": bearer_token})
    assert r.status_code == 200
    data = r.json()
    assert data["full_name"] == "John Doe"

    r = await client.put("/api/profile", json={
        "full_name": "John Updated",
        "phone": "+14155552671"
    }, headers={"Authorization": bearer_token})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["full_name"] == "John Updated"
    assert data["phone"] == "+14155552671"

    r = await client.delete("/api/profile", headers={"Authorization": bearer_token})
    assert r.status_code == 204

    r = await client.get("/api/profile/me", headers={"Authorization": bearer_token})
    assert r.status_code == 404
