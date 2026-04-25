def test_mp_auth_login_creates_user(client):
    response = client.post(
        "/api/v1/mp/auth/login",
        headers={
            "X-Login-Code": "login-code-user-1",
            "X-System-Version": "iOS 17.0",
            "X-Device-UUID": "device-1",
        },
        json={},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_token"]
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] > 0
    assert data["is_new_user"] is True
    assert data["role"] == "user"


def test_mp_auth_login_second_time_is_existing_user(client):
    headers = {
        "X-Login-Code": "login-code-user-1",
        "X-System-Version": "iOS 17.0",
        "X-Device-UUID": "device-1",
    }
    client.post("/api/v1/mp/auth/login", headers=headers, json={})
    response = client.post("/api/v1/mp/auth/login", headers=headers, json={})
    assert response.status_code == 200
    assert response.json()["data"]["is_new_user"] is False
