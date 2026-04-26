from sqlalchemy import select

from app.db.models.distributor import DistributorProfile, DistributorWithdrawal
from app.db.models.user import User


def seed_pending_withdrawal(db_session):
    user = User(openid="withdraw-user-openid", unionid="withdraw-user-union", nickname="提现测试用户", is_distributor=True, role="distributor")
    db_session.add(user)
    db_session.flush()
    db_session.add(
        DistributorProfile(
            user_id=user.id,
            distributor_level="city",
            quota_total=100,
            quota_used=10,
            unsettled_commission=500,
            total_commission=500,
        )
    )
    db_session.add(
        DistributorWithdrawal(
            withdraw_id="wd_admin_001",
            user_id=user.id,
            amount=300,
            account_name="提现测试用户",
            bank_name="微信零钱",
            bank_account_masked="o0-***1234",
            status="pending_review",
        )
    )
    db_session.commit()
    return user.id


def test_admin_distributor_withdrawals_list_returns_pending_records(client, db_session):
    seed_pending_withdrawal(db_session)

    response = client.get("/api/v1/admin/distributor/withdrawals?page=1&page_size=20&status=pending_review")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["list"][0]["withdraw_id"] == "wd_admin_001"
    assert data["list"][0]["status"] == "pending_review"


def test_admin_distributor_withdrawal_approve_marks_paid(client, db_session):
    user_id = seed_pending_withdrawal(db_session)

    response = client.post("/api/v1/admin/distributor/withdrawals/wd_admin_001/approve", json={})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "paid"
    assert data["transfer_bill_no"].startswith("fake-transfer-")
    withdrawal = db_session.execute(select(DistributorWithdrawal).where(DistributorWithdrawal.withdraw_id == "wd_admin_001")).scalar_one()
    profile = db_session.execute(select(DistributorProfile).where(DistributorProfile.user_id == user_id)).scalar_one()
    assert withdrawal.status == "paid"
    assert profile.total_withdrawn_amount == 300


def test_admin_distributor_withdrawal_reject_returns_amount_to_balance(client, db_session):
    user_id = seed_pending_withdrawal(db_session)

    response = client.post("/api/v1/admin/distributor/withdrawals/wd_admin_001/reject", json={})

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "rejected"
    withdrawal = db_session.execute(select(DistributorWithdrawal).where(DistributorWithdrawal.withdraw_id == "wd_admin_001")).scalar_one()
    profile = db_session.execute(select(DistributorProfile).where(DistributorProfile.user_id == user_id)).scalar_one()
    assert withdrawal.status == "rejected"
    assert profile.unsettled_commission == 800
