import json
import hmac
import hashlib

import pytest
import requests

from app.core.config import Settings
from app.core.errors import ValidationError
from app.integrations.wechat_pay import RealWechatPayClient


class ResponseStub:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = json.dumps(self._payload, ensure_ascii=False)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("boom", response=self)


def build_settings():
    return Settings(
        wechat_app_id="wx123",
        wechat_mch_id="mch123",
        wechat_notify_url="https://example.com/notify",
        wechat_transfer_scene_id="1005",
        wechat_transfer_remark="分销佣金提现",
        wechat_transfer_user_recv_perception="劳务报酬",
        wechat_transfer_report_primary="校园分销",
        wechat_transfer_report_secondary="分销佣金提现",
    )


def test_transfer_to_balance_builds_scene_payload(monkeypatch):
    client = RealWechatPayClient(build_settings())
    client._build_authorization = lambda method, url_path, body_text: "AUTH"
    captured = {}

    def fake_post(url, data, timeout, headers):
        captured["url"] = url
        captured["payload"] = json.loads(data.decode("utf-8"))
        captured["headers"] = headers
        return ResponseStub(payload={"out_bill_no": "wd1", "transfer_bill_no": "bill1", "state": "SUCCESS"})

    monkeypatch.setattr(requests, "post", fake_post)

    result = client.transfer_to_balance(out_bill_no="wd1", amount=100, openid="openid-1", user_name="昵称")

    assert result.transfer_bill_no == "bill1"
    assert captured["payload"]["transfer_scene_id"] == "1005"
    assert captured["payload"]["user_recv_perception"] == "劳务报酬"
    assert captured["payload"]["notify_url"] == "https://example.com/notify"
    assert captured["payload"]["transfer_scene_report_infos"] == [
        {"info_type": "岗位类型", "info_content": "校园分销"},
        {"info_type": "报酬说明", "info_content": "分销佣金提现"},
    ]
    assert "user_name" not in captured["payload"]


def test_transfer_to_balance_raises_validation_error_with_wechat_message(monkeypatch):
    client = RealWechatPayClient(build_settings())
    client._build_authorization = lambda method, url_path, body_text: "AUTH"

    def fake_post(url, data, timeout, headers):
        return ResponseStub(
            status_code=400,
            payload={"code": "PARAM_ERROR", "message": "openid和appid不匹配"},
        )

    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(ValidationError) as exc:
        client.transfer_to_balance(out_bill_no="wd2", amount=100, openid="openid-2", user_name="昵称")

    assert "PARAM_ERROR" in exc.value.message
    assert "openid和appid不匹配" in exc.value.message


def test_transfer_to_balance_uses_default_remark_when_setting_is_blank(monkeypatch):
    settings = build_settings()
    settings.wechat_transfer_remark = ""
    settings.wechat_transfer_user_recv_perception = ""
    client = RealWechatPayClient(settings)
    client._build_authorization = lambda method, url_path, body_text: "AUTH"
    captured = {}

    def fake_post(url, data, timeout, headers):
        captured["payload"] = json.loads(data.decode("utf-8"))
        return ResponseStub(payload={"out_bill_no": "wd3", "transfer_bill_no": "bill3", "state": "SUCCESS"})

    monkeypatch.setattr(requests, "post", fake_post)

    client.transfer_to_balance(out_bill_no="wd3", amount=100, openid="openid-3", user_name="昵称")

    assert captured["payload"]["transfer_remark"] == "分销佣金提现"
    assert captured["payload"]["user_recv_perception"] == "劳务报酬"


def test_query_balance_reads_available_and_pending_amount(monkeypatch):
    client = RealWechatPayClient(build_settings())
    client._build_authorization = lambda method, url_path, body_text: "AUTH"

    def fake_get(url, data=None, timeout=15, headers=None):
        return ResponseStub(payload={"available_amount": 9999, "pending_amount": 123})

    monkeypatch.setattr(requests, "get", fake_get)

    result = client.query_balance(account_type="OPERATION")

    assert result.account_type == "OPERATION"
    assert result.available_amount == 9999
    assert result.pending_amount == 123


def test_real_wechat_pay_client_builds_virtual_payment_params():
    settings = Settings(
        wechat_virtual_offer_id="1450536598",
        wechat_virtual_app_key="wx119f24d9ccbc9c30",
        wechat_virtual_env=0,
    )
    client = RealWechatPayClient(settings)

    params = client.create_virtual_prepay(
        order_id="ORDTEST001",
        amount=9900,
        openid="openid-user-1",
        platform="android",
        session_key="session-key-user-1",
    )

    sign_data = json.loads(params.signData)
    assert params.mode == "short_series_goods"
    assert params.offerId == "1450536598"
    assert sign_data["offerId"] == "1450536598"
    assert sign_data["productId"] == "report_001"
    assert sign_data["goodsPrice"] == 9900
    assert sign_data["outTradeNo"] == "ORDTEST001"
    assert "platform" not in sign_data
    assert params.paySig == hmac.new(
        b"wx119f24d9ccbc9c30",
        "requestVirtualPayment&{}".format(params.signData).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert params.signature == hmac.new(
        b"session-key-user-1",
        params.signData.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def test_real_wechat_pay_client_queries_virtual_order(monkeypatch):
    settings = Settings(
        wechat_app_id="wx123",
        wechat_app_secret="secret123",
        wechat_virtual_offer_id="1450536598",
        wechat_virtual_app_key="wx119f24d9ccbc9c30",
        wechat_virtual_env=0,
    )
    client = RealWechatPayClient(settings)
    captured = {}

    def fake_get(url, params, timeout, verify):
        return ResponseStub(payload={"access_token": "token-1", "expires_in": 7200})

    def fake_post(url, params, data, timeout, verify, headers):
        captured["url"] = url
        captured["params"] = params
        captured["payload"] = json.loads(data.decode("utf-8"))
        captured["headers"] = headers
        return ResponseStub(
            payload={
                "errcode": 0,
                "order_info": {
                    "order_id": "ORDTEST001",
                    "wx_order_id": "wx-order-1",
                    "status": 3,
                    "pay_amount": 9900,
                    "pay_time": "2026-05-20T10:00:00Z",
                },
            }
        )

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    result = client.query_virtual_order(order_id="ORDTEST001", openid="openid-user-1")

    assert result.is_paid is True
    assert result.amount == 9900
    assert result.wx_order_id == "wx-order-1"
    assert captured["url"] == "https://api.weixin.qq.com/xpay/query_order"
    assert captured["payload"]["offer_id"] == "1450536598"
    assert captured["payload"]["order_id"] == "ORDTEST001"
    assert captured["payload"]["openid"] == "openid-user-1"
    body_text = json.dumps(captured["payload"], ensure_ascii=False, separators=(",", ":"))
    assert captured["params"]["pay_sig"] == hmac.new(
        b"wx119f24d9ccbc9c30",
        "/xpay/query_order&{}".format(body_text).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
