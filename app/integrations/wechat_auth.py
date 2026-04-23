from dataclasses import dataclass

from app.core.errors import AuthError


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

