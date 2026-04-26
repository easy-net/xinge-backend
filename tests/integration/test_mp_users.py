from sqlalchemy import select

from app.db.models.distributor import DistributorProfile
from app.db.models.user import User


def test_mp_users_me_returns_profile(client):
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
        "/api/v1/mp/users/me",
        headers={
            "X-Login-Code": "login-code-user-1",
            "X-System-Version": "iOS 17.0",
            "X-Device-UUID": "device-1",
        },
        json={},
    )

    assert response.status_code == 200
    assert response.json()["data"]["user_id"] > 0


def test_mp_users_me_returns_real_distributor_fields(client, db_session):
    login_response = client.post(
        "/api/v1/mp/auth/login",
        headers={
            "X-Login-Code": "login-code-user-1",
            "X-System-Version": "iOS 17.0",
            "X-Device-UUID": "device-1",
        },
        json={},
    )
    user_id = login_response.json()["user_info"]["user_id"]
    user = db_session.execute(select(User).where(User.id == user_id)).scalar_one()
    user.is_distributor = True
    db_session.add(
        DistributorProfile(
            user_id=user_id,
            distributor_level="city",
            parent_distributor_id=999,
            quota_total=200,
            quota_used=10,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/mp/users/me",
        headers={
            "X-Login-Code": "login-code-user-1",
            "X-System-Version": "iOS 17.0",
            "X-Device-UUID": "device-1",
        },
        json={},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["distributor_level"] == "city"
    assert data["parent_distributor_id"] == 999


def test_mp_users_me_update_changes_profile(client):
    client.post(
        "/api/v1/mp/auth/login",
        headers={
            "X-Login-Code": "login-code-user-1",
            "X-System-Version": "iOS 17.0",
            "X-Device-UUID": "device-1",
        },
        json={},
    )

    update_response = client.post(
        "/api/v1/mp/users/me/update",
        headers={
            "X-Login-Code": "login-code-user-1",
            "X-System-Version": "iOS 17.0",
            "X-Device-UUID": "device-1",
        },
        json={"nickname": "张三", "avatar_url": "https://example.com/avatar.png"},
    )

    assert update_response.status_code == 200

    me_response = client.post(
        "/api/v1/mp/users/me",
        headers={
            "X-Login-Code": "login-code-user-1",
            "X-System-Version": "iOS 17.0",
            "X-Device-UUID": "device-1",
        },
        json={},
    )

    assert me_response.status_code == 200
    assert me_response.json()["data"]["nickname"] == "张三"


def test_mp_users_me_accepts_bearer_token_without_login_code(client):
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
        "/api/v1/mp/users/me",
        headers={
            "Authorization": "Bearer {}".format(access_token),
        },
        json={},
    )

    assert response.status_code == 200
    assert response.json()["data"]["user_id"] > 0
