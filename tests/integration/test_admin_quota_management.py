from sqlalchemy import select

from app.db.models.distributor import DistributorProfile
from app.db.models.user import User


def seed_quota_management_data(db_session):
    parent = User(openid="quota-parent", unionid="quota-parent-union", nickname="战略分销", is_distributor=True, role="distributor")
    child = User(openid="quota-child", unionid="quota-child-union", nickname="校园分销", is_distributor=True, role="distributor")
    db_session.add_all([parent, child])
    db_session.flush()
    db_session.add(
        DistributorProfile(
            user_id=parent.id,
            distributor_level="city",
            quota_total=300,
            quota_used=50,
        )
    )
    db_session.add(
        DistributorProfile(
            user_id=child.id,
            distributor_level="campus",
            parent_distributor_id=parent.id,
            quota_total=20,
            quota_used=5,
        )
    )
    db_session.commit()
    return parent.id, child.id


def test_admin_distributor_users_lists_profiles(client, db_session):
    parent_id, _ = seed_quota_management_data(db_session)

    response = client.get("/api/v1/admin/distributor/users?page=1&page_size=20")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] >= 3
    assert any(item["user_id"] == parent_id for item in data["list"])


def test_admin_distributor_user_downlines_returns_direct_downlines(client, db_session):
    parent_id, child_id = seed_quota_management_data(db_session)

    response = client.get(f"/api/v1/admin/distributor/users/{parent_id}/downlines?page=1&page_size=20")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["source_user_id"] == parent_id
    assert data["total"] == 1
    assert data["list"][0]["user_id"] == child_id


def test_admin_distributor_quota_allocate_updates_both_profiles(client, db_session):
    parent_id, child_id = seed_quota_management_data(db_session)

    response = client.post(
        f"/api/v1/admin/distributor/users/{parent_id}/quota/allocate",
        json={"downline_user_id": child_id, "amount": 30},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["allocated_amount"] == 30
    assert data["source_user_id"] == parent_id
    assert data["downline_quota"]["user_id"] == child_id
    parent_profile = db_session.execute(select(DistributorProfile).where(DistributorProfile.user_id == parent_id)).scalar_one()
    child_profile = db_session.execute(select(DistributorProfile).where(DistributorProfile.user_id == child_id)).scalar_one()
    assert parent_profile.quota_used == 80
    assert child_profile.quota_total == 50


def test_default_admin_can_allocate_quota_to_any_existing_user(client, db_session):
    target = User(openid="quota-any-user", unionid="quota-any-union", nickname="普通用户")
    db_session.add(target)
    db_session.commit()
    admin_user = db_session.execute(select(User).where(User.openid == "system-admin-openid")).scalar_one()

    downlines_response = client.get(f"/api/v1/admin/distributor/users/{admin_user.id}/downlines?page=1&page_size=20")
    assert downlines_response.status_code == 200
    assert any(item["user_id"] == target.id for item in downlines_response.json()["data"]["list"])

    response = client.post(
        f"/api/v1/admin/distributor/users/{admin_user.id}/quota/allocate",
        json={"downline_user_id": target.id, "amount": 40},
    )

    assert response.status_code == 200
    db_session.expire_all()
    updated_target = db_session.execute(select(User).where(User.id == target.id)).scalar_one()
    target_profile = db_session.execute(select(DistributorProfile).where(DistributorProfile.user_id == target.id)).scalar_one()
    assert updated_target.is_distributor is True
    assert target_profile.parent_distributor_id == admin_user.id
    assert target_profile.quota_total == 40
