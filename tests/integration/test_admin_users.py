from sqlalchemy import select

from app.db.models.distributor import DistributorProfile
from app.db.models.user import User


def test_admin_create_distributor_user_creates_profile(client, db_session):
    response = client.post(
        "/api/v1/admin/users",
        json={
            "openid": "admin-created-openid-1",
            "unionid": "admin-created-unionid-1",
            "nickname": "新分销商",
            "role": "distributor",
            "distributor_level": "campus",
            "quota_total": 25,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "created"

    user = db_session.execute(select(User).where(User.openid == "admin-created-openid-1")).scalar_one()
    profile = db_session.execute(select(DistributorProfile).where(DistributorProfile.user_id == user.id)).scalar_one()
    assert user.role == "distributor"
    assert user.is_distributor is True
    assert profile.distributor_level == "campus"
    assert profile.quota_total == 25


def test_admin_delete_user_removes_plain_user(client, db_session):
    user = User(openid="delete-me-openid", unionid="delete-me-unionid", nickname="待删除用户", role="user", is_distributor=False)
    db_session.add(user)
    db_session.commit()
    user_id = user.id

    response = client.post(f"/api/v1/admin/users/{user_id}/delete", json={})

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "deleted"
    assert db_session.execute(select(User).where(User.id == user_id)).scalar_one_or_none() is None
