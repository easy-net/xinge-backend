import pytest

from app.core.errors import AuthError
from app.integrations.wechat_auth import DevBypassWechatAuthClient, RealWechatAuthClient


def test_dev_bypass_generates_stable_openid():
    client = DevBypassWechatAuthClient()
    result = client.code_to_session("abc-123")
    assert result.openid == "dev-openid-abc-123"


def test_dev_bypass_generates_phone_number():
    client = DevBypassWechatAuthClient()
    assert client.decrypt_phone_number("phone-code-5678") == "13800005678"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self):
        self.get_calls = []
        self.post_calls = []
        self.token_payloads = []
        self.phone_payloads = []
        self.session_payloads = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        if url.endswith("/cgi-bin/token"):
            return FakeResponse(self.token_payloads.pop(0))
        if url.endswith("/sns/jscode2session"):
            return FakeResponse(self.session_payloads.pop(0))
        raise AssertionError("unexpected GET url: {}".format(url))

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        if url.endswith("/wxa/business/getuserphonenumber"):
            return FakeResponse(self.phone_payloads.pop(0))
        raise AssertionError("unexpected POST url: {}".format(url))


def test_real_client_decrypts_phone_number_and_caches_access_token():
    http_client = FakeHttpClient()
    http_client.token_payloads = [{"access_token": "access-1", "expires_in": 7200}]
    http_client.phone_payloads = [
        {"errcode": 0, "errmsg": "ok", "phone_info": {"phoneNumber": "13800138000"}},
        {"errcode": 0, "errmsg": "ok", "phone_info": {"purePhoneNumber": "13900139000"}},
    ]

    client = RealWechatAuthClient(
        app_id="wx-app-id",
        app_secret="wx-app-secret",
        http_client=http_client,
        now_fn=lambda: 1000,
    )

    assert client.decrypt_phone_number("phone-code-1") == "13800138000"
    assert client.decrypt_phone_number("phone-code-2") == "13900139000"
    assert len(http_client.get_calls) == 1
    assert len(http_client.post_calls) == 2
    first_post_url, first_post_kwargs = http_client.post_calls[0]
    assert first_post_url.endswith("/wxa/business/getuserphonenumber")
    assert first_post_kwargs["params"]["access_token"] == "access-1"
    assert first_post_kwargs["json"] == {"code": "phone-code-1"}


def test_real_client_refreshes_access_token_when_wechat_returns_expired():
    http_client = FakeHttpClient()
    http_client.token_payloads = [
        {"access_token": "stale-token", "expires_in": 7200},
        {"access_token": "fresh-token", "expires_in": 7200},
    ]
    http_client.phone_payloads = [
        {"errcode": 40001, "errmsg": "invalid credential"},
        {"errcode": 0, "errmsg": "ok", "phone_info": {"phoneNumber": "13800138000"}},
    ]

    client = RealWechatAuthClient(
        app_id="wx-app-id",
        app_secret="wx-app-secret",
        http_client=http_client,
        now_fn=lambda: 1000,
    )

    assert client.decrypt_phone_number("phone-code-1") == "13800138000"
    assert len(http_client.get_calls) == 2
    assert http_client.post_calls[0][1]["params"]["access_token"] == "stale-token"
    assert http_client.post_calls[1][1]["params"]["access_token"] == "fresh-token"


def test_real_client_code_to_session_surfaces_wechat_error():
    http_client = FakeHttpClient()
    http_client.session_payloads = [{"errcode": 40029, "errmsg": "invalid code"}]
    client = RealWechatAuthClient(
        app_id="wx-app-id",
        app_secret="wx-app-secret",
        http_client=http_client,
    )

    with pytest.raises(AuthError, match="invalid code"):
        client.code_to_session("bad-login-code")
