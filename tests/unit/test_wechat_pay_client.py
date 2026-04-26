import json

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
