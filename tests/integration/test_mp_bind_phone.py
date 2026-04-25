def test_mp_bind_phone_updates_masked_phone(client):
    client.post(
        "/api/v1/mp/auth/login",
        headers={
            "X-Login-Code": "login-code-user-1",
            "X-System-Version": "iOS 17.0",
            "X-Device-UUID": "device-1",
        },
        json={},
    )

    response = client.post(
        "/api/v1/mp/auth/bind-phone",
        headers={
            "X-Login-Code": "login-code-user-1",
            "X-System-Version": "iOS 17.0",
            "X-Device-UUID": "device-1",
        },
        json={"phone_code": "phone-code-user-1"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["phone_masked"] == "138****8000"


def test_mp_bind_phone_accepts_bearer_token(client):
    login_response = client.post(
        "/api/v1/mp/auth/login",
        headers={
            "X-Login-Code": "login-code-user-1",
            "X-System-Version": "iOS 17.0",
            "X-Device-UUID": "device-1",
        },
        json={},
    )
    access_token = login_response.json()["data"]["access_token"]

    response = client.post(
        "/api/v1/mp/auth/bind-phone",
        headers={
            "Authorization": "Bearer {}".format(access_token),
        },
        json={"phone_code": "phone-code-user-1"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["phone_masked"] == "138****8000"
