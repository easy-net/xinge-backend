from sqlalchemy import select

from app.db.models.distributor import DistributorApplication, DistributorProfile
from app.db.models.message import Message
from app.db.models.user import User

from tests.integration.test_mp_reports_crud import auth_headers


def seed_pending_application(client, db_session):
    login_response = client.post("/api/v1/mp/auth/login", headers=auth_headers(), json={})
    user_id = login_response.json()["user_info"]["user_id"]
    db_session.add(
        DistributorApplication(
            application_id="app_admin_001",
            user_id=user_id,
            real_name="张三",
            phone="13800138000",
            reason="希望代理校园市场",
            status="pending",
            target_level="campus",
        )
    )
    db_session.commit()
    return user_id


def test_admin_distributor_applications_list_returns_pending_records(client, db_session):
    seed_pending_application(client, db_session)

    response = client.get("/api/v1/admin/distributor/applications?page=1&page_size=20&status=pending")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["list"][0]["application_id"] == "app_admin_001"
    assert data["list"][0]["real_name"] == "张三"


def test_admin_distributor_application_approve_sets_user_and_profile(client, db_session):
    user_id = seed_pending_application(client, db_session)

    response = client.post("/api/v1/admin/distributor/applications/app_admin_001/approve", json={})

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "approved"
    user = db_session.execute(select(User).where(User.id == user_id)).scalar_one()
    assert user.is_distributor is True
    profile = db_session.execute(select(DistributorProfile).where(DistributorProfile.user_id == user_id)).scalar_one()
    assert profile.distributor_level == "campus"
    message = db_session.execute(select(Message).where(Message.user_id == user_id)).scalar_one()
    assert message.type == "distributor_approved"


def test_admin_distributor_application_reject_sets_reason_and_message(client, db_session):
    user_id = seed_pending_application(client, db_session)

    response = client.post(
        "/api/v1/admin/distributor/applications/app_admin_001/reject",
        json={"reject_reason": "资料不完整"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "rejected"
    application = db_session.execute(
        select(DistributorApplication).where(DistributorApplication.application_id == "app_admin_001")
    ).scalar_one()
    assert application.reject_reason == "资料不完整"
    message = db_session.execute(select(Message).where(Message.user_id == user_id)).scalar_one()
    assert message.type == "distributor_rejected"


def test_admin_assign_downline_updates_parent_and_distributor_profile(client, db_session):
    parent = User(openid="parent-openid", unionid="parent-unionid", nickname="上级分销", role="distributor", is_distributor=True)
    child = User(openid="child-openid", unionid="child-unionid", nickname="候选用户", role="user", is_distributor=False)
    db_session.add_all([parent, child])
    db_session.flush()
    db_session.add(DistributorProfile(user_id=parent.id, distributor_level="strategic", quota_total=500))
    db_session.commit()

    response = client.post(
        f"/api/v1/admin/distributor/users/{parent.id}/downlines/assign",
        json={"downline_user_id": child.id, "distributor_level": "city"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "assigned"
    assert data["parent_distributor_id"] == parent.id
    assert data["distributor_level"] == "city"

    updated_child = db_session.execute(select(User).where(User.id == child.id)).scalar_one()
    updated_profile = db_session.execute(select(DistributorProfile).where(DistributorProfile.user_id == child.id)).scalar_one()
    assert updated_child.is_distributor is True
    assert updated_child.role == "distributor"
    assert updated_profile.parent_distributor_id == parent.id
    assert updated_profile.distributor_level == "city"


def test_admin_unassign_downline_clears_parent_relation(client, db_session):
    parent = User(openid="parent-openid-2", unionid="parent-unionid-2", nickname="上级分销2", role="distributor", is_distributor=True)
    child = User(openid="child-openid-2", unionid="child-unionid-2", nickname="候选用户2", role="distributor", is_distributor=True)
    db_session.add_all([parent, child])
    db_session.flush()
    db_session.add(DistributorProfile(user_id=parent.id, distributor_level="strategic", quota_total=500))
    db_session.add(DistributorProfile(user_id=child.id, distributor_level="city", parent_distributor_id=parent.id, quota_total=0))
    db_session.commit()

    response = client.post(
        f"/api/v1/admin/distributor/users/{parent.id}/downlines/unassign",
        json={"downline_user_id": child.id},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "unassigned"
    assert data["parent_distributor_id"] is None

    updated_profile = db_session.execute(select(DistributorProfile).where(DistributorProfile.user_id == child.id)).scalar_one()
    assert updated_profile.parent_distributor_id is None
