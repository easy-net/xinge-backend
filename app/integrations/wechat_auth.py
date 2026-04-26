import time
import logging
from dataclasses import dataclass

from app.core.errors import AuthError

logger = logging.getLogger(__name__)

@dataclass
class WechatSessionInfo:
    openid: str
    unionid: str = ""


class WechatAuthClient:
    def code_to_session(self, login_code: str) -> WechatSessionInfo:
        raise NotImplementedError

    def decrypt_phone_number(self, phone_code: str) -> str:
        raise NotImplementedError


class NullWechatAuthClient(WechatAuthClient):
    def code_to_session(self, login_code: str) -> WechatSessionInfo:
        raise AuthError(message="wechat auth client is not configured")

    def decrypt_phone_number(self, phone_code: str) -> str:
        raise AuthError(message="wechat auth client is not configured")


class DevBypassWechatAuthClient(WechatAuthClient):
    def code_to_session(self, login_code: str) -> WechatSessionInfo:
        safe = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in login_code)[:64]
        return WechatSessionInfo(openid="dev-openid-{}".format(safe), unionid="dev-unionid-{}".format(safe))

    def decrypt_phone_number(self, phone_code: str) -> str:
        suffix = "".join(ch for ch in phone_code if ch.isdigit())[-4:]
        suffix = suffix.rjust(4, "0")
        return "1380000{}".format(suffix)


class RealWechatAuthClient(WechatAuthClient):
    def __init__(self, app_id: str, app_secret: str, http_client=None, now_fn=None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.http_client = http_client or self._load_http_client()
        self.now_fn = now_fn or time.time
        self._access_token = ""
        self._access_token_expires_at = 0.0

    @staticmethod
    def _load_http_client():
        try:
            import requests
        except ImportError as exc:
            raise AuthError(message="requests is required for real wechat auth") from exc
        return requests

    def _request_json(self, method: str, url: str, **kwargs) -> dict:
        request = getattr(self.http_client, method.lower())
        try:
            response = request(url, timeout=10, **kwargs)
            response.raise_for_status()
        except Exception as exc:
            logger.exception("wechat request failed url=%s method=%s", url, method)
            raise AuthError(message="wechat service is unavailable") from exc
        payload = response.json()
        if not isinstance(payload, dict):
            raise AuthError(message="invalid response from wechat service")
        return payload

    def _extract_wechat_error(self, payload: dict) -> str:
        errmsg = payload.get("errmsg")
        errcode = payload.get("errcode")
        if errmsg and errcode not in (None, 0):
            return "{} ({})".format(errmsg, errcode)
        if errmsg:
            return str(errmsg)
        if errcode not in (None, 0):
            return "wechat error ({})".format(errcode)
        return "wechat request failed"

    def _fetch_access_token(self) -> tuple[str, int]:
        payload = self._request_json(
            "get",
            "https://api.weixin.qq.com/cgi-bin/token",
            params={
                "grant_type": "client_credential",
                "appid": self.app_id,
                "secret": self.app_secret,
            },
        )
        if "access_token" not in payload:
            raise AuthError(message=self._extract_wechat_error(payload))
        expires_in = int(payload.get("expires_in", 7200))
        return payload["access_token"], expires_in

    def _get_access_token(self, *, force_refresh: bool = False) -> str:
        now = self.now_fn()
        if not force_refresh and self._access_token and now < self._access_token_expires_at:
            return self._access_token

        access_token, expires_in = self._fetch_access_token()
        ttl = max(expires_in - 60, 60)
        self._access_token = access_token
        self._access_token_expires_at = now + ttl
        return self._access_token

    def code_to_session(self, login_code: str) -> WechatSessionInfo:
        payload = self._request_json(
            "get",
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": self.app_id,
                "secret": self.app_secret,
                "js_code": login_code,
                "grant_type": "authorization_code",
            },
        )
        logger.info("wechat auth response: %s", payload)
        if "openid" not in payload:
            raise AuthError(message=self._extract_wechat_error(payload))
        return WechatSessionInfo(openid=payload["openid"], unionid=payload.get("unionid", ""))

    def decrypt_phone_number(self, phone_code: str) -> str:
        for attempt in range(2):
            access_token = self._get_access_token(force_refresh=attempt > 0)
            payload = self._request_json(
                "post",
                "https://api.weixin.qq.com/wxa/business/getuserphonenumber",
                params={"access_token": access_token},
                json={"code": phone_code},
            )
            errcode = payload.get("errcode", 0)
            if errcode in (0, None):
                phone_info = payload.get("phone_info") or {}
                phone_number = phone_info.get("phoneNumber") or phone_info.get("purePhoneNumber")
                if not phone_number:
                    raise AuthError(message="invalid phone payload from wechat")
                return phone_number
            if errcode not in (40001, 42001):
                raise AuthError(message=self._extract_wechat_error(payload))

        raise AuthError(message="wechat access token is invalid or expired")
