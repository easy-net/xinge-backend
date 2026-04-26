from app.integrations.wechat_auth import WechatAuthClient, WechatSessionInfo
from app.integrations.wechat_pay import BalanceResult, PaymentParams, TransferResult, WechatPayClient


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
