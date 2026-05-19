import hashlib
import hmac
import json

from app.integrations.wechat_auth import WechatAuthClient, WechatSessionInfo
from app.integrations.wechat_pay import BalanceResult, PaymentParams, TransferResult, VirtualPaymentParams, WechatPayClient


FAKE_QRCODE_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBgN8Xl3sAAAAASUVORK5CYII="
)


class FakeWechatAuthClient(WechatAuthClient):
    def __init__(self, session_map=None, phone_map=None):
        self.session_map = session_map or {}
        self.phone_map = phone_map or {}

    def code_to_session(self, login_code: str) -> WechatSessionInfo:
        session = self.session_map[login_code]
        if len(session) == 3:
            openid, unionid, session_key = session
        else:
            openid, unionid = session
            session_key = "session-key-{}".format(openid)
        return WechatSessionInfo(openid=openid, unionid=unionid, session_key=session_key)

    def decrypt_phone_number(self, phone_code: str) -> str:
        return self.phone_map[phone_code]

    def create_unlimited_qrcode(
        self,
        *,
        scene: str,
        page: str,
        env_version: str = "release",
        width: int = 430,
        check_path: bool = True,
    ) -> bytes:
        del scene, page, env_version, width, check_path
        import base64

        return base64.b64decode(FAKE_QRCODE_PNG_BASE64)


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

    def create_virtual_prepay(
        self,
        *,
        order_id: str,
        amount: int,
        openid: str,
        platform: str = "android",
        session_key: str = "",
    ) -> VirtualPaymentParams:
        sign_payload = {
            "offerId": "1450536598",
            "buyQuantity": 1,
            "env": 0,
            "currencyType": "CNY",
            "platform": platform,
            "productId": order_id,
            "goodsPrice": int(amount),
            "outTradeNo": order_id,
        }
        sign_data = json.dumps(sign_payload, ensure_ascii=False, separators=(",", ":"))
        return VirtualPaymentParams(
            mode="short_series_goods",
            signData=sign_data,
            paySig=hmac.new(b"wx119f24d9ccbc9c30", "requestVirtualPayment&{}".format(sign_data).encode("utf-8"), hashlib.sha256).hexdigest(),
            signature=hmac.new((session_key or "fake-session-key").encode("utf-8"), sign_data.encode("utf-8"), hashlib.sha256).hexdigest(),
            offerId="1450536598",
            buyQuantity=1,
            env=0,
            currencyType="CNY",
            platform=platform,
            productId=order_id,
            goodsPrice=int(amount),
            outTradeNo=order_id,
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

    def transfer_to_balance(self, *, out_bill_no: str, amount: int, openid: str, user_name: str = "") -> TransferResult:
        return TransferResult(
            out_bill_no=out_bill_no,
            transfer_bill_no="fake-transfer-{}".format(out_bill_no),
            state="SUCCESS",
            package_info="fake",
        )

    def query_balance(self, *, account_type: str) -> BalanceResult:
        normalized = (account_type or "").strip().upper() or "OPERATION"
        fixtures = {
            "OPERATION": BalanceResult(account_type="OPERATION", available_amount=123456, pending_amount=2000),
            "BASIC": BalanceResult(account_type="BASIC", available_amount=456789, pending_amount=0),
            "FEES": BalanceResult(account_type="FEES", available_amount=7890, pending_amount=0),
        }
        return fixtures.get(normalized, BalanceResult(account_type=normalized, available_amount=0, pending_amount=0))
