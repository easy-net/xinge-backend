from sqlalchemy import select

from app.db.models.distributor import DistributorProfile, DistributorWithdrawal
from app.db.models.user import User


def seed_debug_withdrawal(db_session, *, withdraw_id="WD202604280001", status="processing", amount=5000):
    user = User(openid=f"debug-openid-{withdraw_id}", unionid=f"debug-unionid-{withdraw_id}", nickname="调试分销商", role="distributor", is_distributor=True)
    db_session.add(user)
    db_session.flush()
    db_session.add(
        DistributorProfile(
            user_id=user.id,
            distributor_level="city",
            quota_total=50,
            unsettled_commission=0,
        )
    )
    db_session.add(
        DistributorWithdrawal(
            withdraw_id=withdraw_id,
            user_id=user.id,
            amount=amount,
            account_name="调试分销商",
            bank_name="微信零钱",
            bank_account_masked="138****0000",
            status=status,
        )
    )
    db_session.commit()
    return user.id


def test_admin_get_withdrawal_debug_returns_diagnostics(client, db_session):
    seed_debug_withdrawal(db_session, withdraw_id="WD202604280101")

    response = client.get("/api/v1/admin/distributor/withdrawals/WD202604280101")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["withdraw_id"] == "WD202604280101"
    assert data["status"] == "processing"
    assert data["diagnostics"]["waiting_callback"] is True


def test_admin_debug_withdrawal_callback_marks_paid(client, db_session):
    seed_debug_withdrawal(db_session, withdraw_id="WD202604280102")

    response = client.post(
        "/api/v1/admin/distributor/withdrawals/WD202604280102/debug-callback",
        json={"state": "SUCCESS"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "paid"
    withdrawal = db_session.execute(
        select(DistributorWithdrawal).where(DistributorWithdrawal.withdraw_id == "WD202604280102")
    ).scalar_one()
    assert withdrawal.status == "paid"
