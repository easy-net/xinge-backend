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
