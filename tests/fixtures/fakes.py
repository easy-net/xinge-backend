from app.integrations.wechat_auth import WechatAuthClient, WechatSessionInfo
from app.integrations.wechat_pay import PaymentParams, WechatPayClient


class FakeWechatAuthClient(WechatAuthClient):
    def __init__(self, session_map=None, phone_map=None):
        self.session_map = session_map or {}
        self.phone_map = phone_map or {}

    def code_to_session(self, login_code: str) -> WechatSessionInfo:
        openid, unionid = self.session_map[login_code]
        return WechatSessionInfo(openid=openid, unionid=unionid)

    def decrypt_phone_number(self, phone_code: str) -> str:
        return self.phone_map[phone_code]


class FakeWechatPayClient(WechatPayClient):
    def create_prepay(self, *, order_id: str, amount: int, openid: str) -> PaymentParams:
        return PaymentParams(
            timeStamp="1713600000",
            nonceStr="nonce-{}".format(order_id[-6:]),
            package="prepay_id={}".format(order_id),
            signType="RSA",
            paySign="sign-{}".format(amount),
            prepay_id="prepay-{}".format(order_id),
        )

    def parse_notification(self, payload: dict):
        from app.integrations.wechat_pay import PaymentNotification

        return PaymentNotification(
            notify_id=payload["notify_id"],
            order_id=payload["order_id"],
            amount=payload["amount"],
            status=payload.get("status", "success"),
            paid_at=payload.get("paid_at", "2026-04-20T10:00:00Z"),
        )
