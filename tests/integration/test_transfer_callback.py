import pytest
from app.db.models.distributor import DistributorProfile, DistributorWithdrawal
from app.db.models.user import User


class FakeWechatPayClientWithDecrypt:
    """模拟支持解密的微信支付客户端"""
    
    def decrypt_callback_resource(self, resource):
        # 模拟解密后的数据
        return {
            "transfer_bill_no": "TRANS_123456",
            "out_bill_no": "WD20250426120000100001",
            "state": "SUCCESS",
        }


class FakeWechatPayClientWithDecryptFailed:
    """模拟转账失败的微信支付客户端"""
    
    def decrypt_callback_resource(self, resource):
        return {
            "transfer_bill_no": "TRANS_123457",
            "out_bill_no": "WD20250426120000100002",
            "state": "FAILED",
        }


def create_test_user_and_withdrawal(db_session, withdraw_id, status="processing"):
    """创建测试用户和提现记录"""
    user = User(
        openid=f"test-openid-{withdraw_id}",
        unionid=f"test-unionid-{withdraw_id}",
        nickname="测试用户",
        role="distributor",
        is_distributor=True,
    )
    db_session.add(user)
    db_session.flush()
    
    profile = DistributorProfile(
        user_id=user.id,
        distributor_level="city",
        quota_total=100,
        quota_used=0,
        unsettled_commission=0,
        total_withdrawn_amount=0,
    )
    db_session.add(profile)
    
    withdrawal = DistributorWithdrawal(
        withdraw_id=withdraw_id,
        user_id=user.id,
        amount=5000,
        account_name="测试用户",
        bank_name="微信零钱",
        bank_account_masked="wx***1234",
        status=status,
    )
    db_session.add(withdrawal)
    db_session.commit()
    
    return user, withdrawal


@pytest.mark.parametrize("mock_client_class,expected_status,expected_withdrawn", [
    (FakeWechatPayClientWithDecrypt, "paid", 5000),
    (FakeWechatPayClientWithDecryptFailed, "failed", 0),
])
def test_wechat_transfer_callback_updates_withdrawal_status(
    client, db_session, mock_client_class, expected_status, expected_withdrawn
):
    """测试微信转账回调正确更新提现状态"""
    withdraw_id = f"WD20250426120000{100001 if expected_status == 'paid' else 100002}"
    user, withdrawal = create_test_user_and_withdrawal(db_session, withdraw_id)
    
    # 设置 mock 客户端
    client.app.state.wechat_pay_client = mock_client_class()
    
    # 发送回调请求（模拟 V3 回调格式）
    payload = {
        "id": "test-notify-id",
        "resource": {
            "original_type": "mch_transfer_bill",
            "algorithm": "AEAD_AES_256_GCM",
            "ciphertext": "mock-ciphertext",
            "associated_data": "",
            "nonce": "mock-nonce",
        }
    }
    
    response = client.post(
        "/api/v1/mp/distributor/withdrawals/notify/wechat",
        json=payload,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "SUCCESS"
    assert data["data"]["withdraw_id"] == withdraw_id
    assert data["data"]["status"] == expected_status
    
    # 验证数据库状态
    db_session.refresh(withdrawal)
    assert withdrawal.status == expected_status
    
    # 验证用户累计提现金额
    db_session.refresh(user.distributor_profile)
    assert user.distributor_profile.total_withdrawn_amount == expected_withdrawn
    
    # 如果是失败，验证余额已退回
    if expected_status == "failed":
        assert user.distributor_profile.unsettled_commission == 5000


def test_wechat_transfer_callback_with_mock_payload(client, db_session):
    """测试使用 Mock 格式的回调（不带 resource）"""
    withdraw_id = "WD20250426120000100003"
    user, withdrawal = create_test_user_and_withdrawal(db_session, withdraw_id)
    
    # 不使用解密客户端
    client.app.state.wechat_pay_client = None
    
    # 发送 Mock 回调
    payload = {
        "transfer_bill_no": "TRANS_MOCK_001",
        "out_bill_no": withdraw_id,
        "state": "SUCCESS",
    }
    
    response = client.post(
        "/api/v1/mp/distributor/withdrawals/notify/wechat",
        json=payload,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "SUCCESS"
    
    # 验证状态已更新
    db_session.refresh(withdrawal)
    assert withdrawal.status == "paid"


def test_wechat_transfer_callback_returns_fail_for_invalid_withdrawal(client, db_session):
    """测试回调不存在的提现记录返回失败"""
    client.app.state.wechat_pay_client = None
    
    payload = {
        "transfer_bill_no": "TRANS_999",
        "out_bill_no": "WD_NOT_EXIST",
        "state": "SUCCESS",
    }
    
    response = client.post(
        "/api/v1/mp/distributor/withdrawals/notify/wechat",
        json=payload,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "FAIL"
