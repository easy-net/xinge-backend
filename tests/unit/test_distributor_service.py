from datetime import datetime

import pytest

from app.core.config import Settings
from app.core.errors import ForbiddenError, NotFoundError
from app.db.models.distributor import DistributorApplication, DistributorProfile, DistributorWithdrawal
from app.db.models.user import User
from app.integrations.wechat_pay import TransferResult
from app.services.distributor_service import DistributorService


def create_distributor_user(db_session):
    user = User(openid="unit-openid", unionid="unit-unionid", is_distributor=True)
    db_session.add(user)
    db_session.flush()
    db_session.add(
        DistributorProfile(
            user_id=user.id,
            distributor_level="campus",
            quota_total=10,
            quota_used=2,
            unsettled_commission=800,
        )
    )
    db_session.flush()
    return user


def test_distributor_service_application_status_raises_when_missing(db_session):
    user = create_distributor_user(db_session)

    with pytest.raises(NotFoundError):
        DistributorService(db_session).application_status(user=user)


def test_distributor_service_list_withdrawals_serializes_items(db_session):
    user = create_distributor_user(db_session)
    db_session.add(
        DistributorWithdrawal(
            withdraw_id="unit-withdraw-1",
            user_id=user.id,
            amount=800,
            account_name="张三",
            bank_name="招商银行",
            bank_account_masked="****7890",
            status="processing",
            completed_at=datetime.utcnow(),
        )
    )
    db_session.commit()

    data = DistributorService(db_session).list_withdrawals(user=user, page=1, page_size=20)

    assert data["total"] == 1
    assert data["list"][0]["withdraw_id"] == "unit-withdraw-1"
    assert data["list"][0]["bank_name"] == "招商银行"


def test_distributor_service_me_requires_profile(db_session):
    user = User(openid="plain-user", unionid="plain-unionid", is_distributor=False)
    db_session.add(user)
    db_session.commit()

    with pytest.raises(ForbiddenError):
        DistributorService(db_session).me(user=user)


def test_distributor_service_application_status_returns_latest_record(db_session):
    user = create_distributor_user(db_session)
    db_session.add(
        DistributorApplication(
            application_id="unit-app-1",
            user_id=user.id,
            real_name="张三",
            phone="13800138000",
            reason="缺少资料",
            status="rejected",
            target_level="campus",
            reject_reason="缺少资料",
        )
    )
    db_session.commit()

    data = DistributorService(db_session).application_status(user=user)

    assert data["application_id"] == "unit-app-1"
    assert data["status"] == "rejected"
    assert data["reject_reason"] == "缺少资料"


def test_distributor_service_apply_returns_created_payload(db_session):
    user = User(openid="apply-openid", unionid="apply-unionid", is_distributor=False)
    db_session.add(user)
    db_session.commit()

    data = DistributorService(db_session).apply(
        user=user,
        payload={
            "phone": "13800138000",
            "real_name": "张三",
            "reason": "希望代理校园市场",
            "target_level": "campus",
        },
    )

    assert data["application_id"].startswith("app_")
    assert data["status"] == "pending"


class WaitUserConfirmWechatPayClient:
    def transfer_to_balance(self, *, out_bill_no: str, amount: int, openid: str, user_name: str = ""):
        return TransferResult(
            out_bill_no=out_bill_no,
            transfer_bill_no="bill-wait-1",
            state="WAIT_USER_CONFIRM",
            package_info="mock-package",
        )


def test_admin_approve_withdrawal_marks_processing_when_wechat_requires_confirmation(db_session):
    user = create_distributor_user(db_session)
    db_session.add(
        DistributorWithdrawal(
            withdraw_id="unit-withdraw-confirm",
            user_id=user.id,
            amount=300,
            account_name="张三",
            bank_name="微信零钱",
            bank_account_masked="o0-***1234",
            status="pending_review",
        )
    )
    db_session.commit()

    data = DistributorService(db_session, WaitUserConfirmWechatPayClient()).admin_approve_withdrawal(
        withdraw_id="unit-withdraw-confirm"
    )

    db_session.refresh(user.distributor_profile)
    withdrawal = db_session.query(DistributorWithdrawal).filter_by(withdraw_id="unit-withdraw-confirm").one()
    assert data["status"] == "processing"
    assert data["transfer_state"] == "WAIT_USER_CONFIRM"
    assert data["package_info"] == "mock-package"
    assert withdrawal.status == "processing"
    assert user.distributor_profile.total_withdrawn_amount == 0


def test_build_wechat_transfer_bill_no_strips_non_alnum(db_session):
    service = DistributorService(db_session)

    value = service._build_wechat_transfer_bill_no("wd_20260426082743_000136")

    assert value == "WD20260426082743000136"


def test_admin_approve_withdrawal_can_bypass_validation(db_session):
    user = create_distributor_user(db_session)
    db_session.add(
        DistributorWithdrawal(
            withdraw_id="wd_20260426082743_000136",
            user_id=user.id,
            amount=300,
            account_name="张三",
            bank_name="微信零钱",
            bank_account_masked="o0-***1234",
            status="pending_review",
        )
    )
    db_session.commit()

    settings = Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///:memory:",
        encryption_key="0123456789abcdef0123456789abcdef",
        unsafe_admin_withdraw_approve=True,
    )
    data = DistributorService(db_session, settings=settings).admin_approve_withdrawal(
        withdraw_id="wd_20260426082743_000136"
    )

    db_session.refresh(user.distributor_profile)
    withdrawal = db_session.query(DistributorWithdrawal).filter_by(withdraw_id="wd_20260426082743_000136").one()
    assert data["status"] == "paid"
    assert data["transfer_state"] == "SUCCESS"
    assert data["transfer_bill_no"].startswith("mock-admin-")
    assert withdrawal.transfer_bill_no.startswith("mock-admin-")
    assert user.distributor_profile.total_withdrawn_amount == 300
