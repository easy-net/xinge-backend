from datetime import datetime

from app.core.errors import NotFoundError, ValidationError
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderService


class XPayGoodsService:
    def __init__(self, db, wechat_pay_client):
        self.db = db
        self.wechat_pay_client = wechat_pay_client
        self.order_repository = OrderRepository(db)

    def process_goods_deliver_notify(self, payload: dict):
        event = payload.get("Event") or payload.get("event") or payload.get("MsgType")
        if event and event != "xpay_goods_deliver_notify":
            raise ValidationError(message="unsupported xpay event")

        order_id = (
            payload.get("out_trade_no")
            or payload.get("outTradeNo")
            or payload.get("order_id")
            or payload.get("OrderId")
            or payload.get("orderId")
        )
        if not order_id:
            raise ValidationError(message="missing xpay order id")

        order = self.order_repository.get_by_order_id(order_id=order_id)
        if order is None:
            raise NotFoundError(message="order not found")

        query_result = self.wechat_pay_client.query_virtual_order(order_id=order.order_id)
        if not query_result.is_paid:
            raise ValidationError(message="payment not successful")
        if query_result.amount and query_result.amount != order.amount:
            raise ValidationError(message="amount mismatch")

        paid_at = query_result.paid_at or datetime.utcnow().isoformat() + "Z"
        OrderService(self.db, self.wechat_pay_client).fulfill_paid_order(
            order_id=order.order_id,
            amount=query_result.amount,
            paid_at=paid_at,
            notify_wechat=False,
        )
        return {"errcode": 0, "errmsg": "ok"}
