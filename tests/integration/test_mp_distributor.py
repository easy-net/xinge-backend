from datetime import datetime, timedelta

from sqlalchemy import select

from app.db.models.distributor import DistributorApplication, DistributorProfile, DistributorWithdrawal
from app.db.models.report import Report
from app.db.models.user import User

from tests.integration.test_mp_reports_crud import auth_headers


def seed_distributor_user(client, db_session):
    login_response = client.post("/api/v1/mp/auth/login", headers=auth_headers(), json={})
    user_id = login_response.json()["user_info"]["user_id"]
    user = db_session.execute(select(User).where(User.id == user_id)).scalar_one()
    user.is_distributor = True
    profile = DistributorProfile(
        user_id=user_id,
        distributor_level="city",
        parent_distributor_id=100,
        quota_total=500,
        quota_used=123,
        total_commission=9900,
        total_sales_amount=99000,
        total_withdrawn_amount=6600,
        unsettled_commission=3300,
    )
    db_session.add(profile)
    db_session.add(
        Report(
            user_id=user_id,
            name="已支付报告",
            form_data={"school_name": "北京大学"},
            status="completed",
            report_type="full",
        )
    )
    db_session.add(
        Report(
            user_id=user_id,
            name="未支付报告",
            form_data={"school_name": "清华大学"},
            status="draft",
            report_type="preview",
        )
    )
    db_session.add(User(openid="downline-openid-city", unionid="downline-unionid-city", is_distributor=True))
    db_session.flush()
    city_downline = db_session.execute(select(User).where(User.openid == "downline-openid-city")).scalar_one()
    db_session.add(
        DistributorProfile(
            user_id=city_downline.id,
            distributor_level="city",
            parent_distributor_id=user_id,
            quota_total=100,
        )
    )
    db_session.add(User(openid="downline-openid-campus", unionid="downline-unionid-campus", is_distributor=True))
    db_session.flush()
    campus_downline = db_session.execute(select(User).where(User.openid == "downline-openid-campus")).scalar_one()
    db_session.add(
        DistributorProfile(
            user_id=campus_downline.id,
            distributor_level="campus",
            parent_distributor_id=user_id,
            quota_total=50,
        )
    )
    db_session.commit()
    return user_id


def test_mp_distributor_me_returns_profile_and_stats(client, db_session):
    user_id = seed_distributor_user(client, db_session)

    response = client.post("/api/v1/mp/distributor/me", headers=auth_headers(), json={})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["user_id"] == user_id
    assert data["distributor_level"] == "city"
    assert data["parent_distributor_id"] == 100
    assert data["quota_total"] == 500
    assert data["quota_used"] == 123
    assert data["quota_remaining"] == 377
    assert data["total_commission"] == 9900
    assert data["withdrawable_amount"] == 3300
    assert data["report_stats"] == {"paid_count": 1, "total_count": 2, "unpaid_count": 1}
    assert data["team_stats"] == {"campus_count": 1, "city_count": 1, "user_count": 2}
    assert data["downline_total"] == 2


def test_mp_distributor_application_status_returns_latest_application(client, db_session):
    user_id = seed_distributor_user(client, db_session)
    now = datetime.utcnow()
    db_session.add(
        DistributorApplication(
            application_id="app_older",
            user_id=user_id,
            status="rejected",
            target_level="campus",
            reject_reason="资料不完整",
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )
    )
    db_session.add(
        DistributorApplication(
            application_id="app_latest",
            user_id=user_id,
            status="pending",
            target_level="city",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    response = client.post("/api/v1/mp/distributor/application/status", headers=auth_headers(), json={})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["application_id"] == "app_latest"
    assert data["status"] == "pending"
    assert data["target_level"] == "city"
    assert data["reject_reason"] is None


def test_mp_distributor_application_status_returns_404_without_records(client):
    client.post("/api/v1/mp/auth/login", headers=auth_headers(), json={})

    response = client.post("/api/v1/mp/distributor/application/status", headers=auth_headers(), json={})

    assert response.status_code == 404
    assert response.json()["message"] == "application not found"


def test_mp_distributor_withdrawals_returns_paginated_history(client, db_session):
    user_id = seed_distributor_user(client, db_session)
    now = datetime.utcnow()
    db_session.add(
        DistributorWithdrawal(
            withdraw_id="wdraw_older",
            user_id=user_id,
            amount=1200,
            account_name="张三",
            bank_name="招商银行",
            bank_account_masked="****1234",
            status="completed",
            completed_at=now - timedelta(days=1),
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=1),
        )
    )
    db_session.add(
        DistributorWithdrawal(
            withdraw_id="wdraw_latest",
            user_id=user_id,
            amount=3300,
            account_name="张三",
            bank_name="建设银行",
            bank_account_masked="****5678",
            status="pending",
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    response = client.post("/api/v1/mp/distributor/withdrawals", headers=auth_headers(), json={"page": 1, "page_size": 20})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert data["list"][0]["withdraw_id"] == "wdraw_latest"
    assert data["list"][0]["bank_account_masked"] == "****5678"
    assert data["list"][1]["withdraw_id"] == "wdraw_older"
    assert data["list"][1]["completed_at"] is not None


def test_mp_distributor_withdrawals_requires_distributor_role(client):
    client.post("/api/v1/mp/auth/login", headers=auth_headers(), json={})

    response = client.post("/api/v1/mp/distributor/withdrawals", headers=auth_headers(), json={"page": 1, "page_size": 20})

    assert response.status_code == 403
    assert response.json()["message"] == "distributor access required"
