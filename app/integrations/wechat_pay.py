from dataclasses import dataclass
from datetime import datetime


@dataclass
class PaymentParams:
    timeStamp: str
    nonceStr: str
    package: str
    signType: str
    paySign: str
    prepay_id: str


@dataclass
class PaymentNotification:
    notify_id: str
    order_id: str
    amount: int
    status: str
    paid_at: str


class WechatPayClient:
    def create_prepay(self, *, order_id: str, amount: int, openid: str) -> PaymentParams:
        raise NotImplementedError

    def parse_notification(self, payload: dict) -> PaymentNotification:
        raise NotImplementedError


class NullWechatPayClient(WechatPayClient):
    def create_prepay(self, *, order_id: str, amount: int, openid: str) -> PaymentParams:
        return PaymentParams(
            timeStamp="1713600000",
            nonceStr="nonce-not-configured",
            package="prepay_id={}".format(order_id),
            signType="RSA",
            paySign="not-configured",
            prepay_id=order_id,
        )

    def parse_notification(self, payload: dict) -> PaymentNotification:
        return PaymentNotification(
            notify_id=payload.get("notify_id", "notify-default"),
            order_id=payload["order_id"],
            amount=payload["amount"],
            status=payload.get("status", "success"),
            paid_at=payload.get("paid_at", datetime.utcnow().isoformat() + "Z"),
        )
