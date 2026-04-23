from app.core.errors import NotFoundError, ValidationError
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_callback_repository import PaymentCallbackRepository
from app.repositories.report_repository import ReportRepository


class PaymentNotifyService:
    def __init__(self, db, wechat_pay_client):
        self.db = db
        self.wechat_pay_client = wechat_pay_client
        self.order_repository = OrderRepository(db)
        self.payment_callback_repository = PaymentCallbackRepository(db)
        self.report_repository = ReportRepository(db)

    def process(self, payload: dict):
        notification = self.wechat_pay_client.parse_notification(payload)
        existing = self.payment_callback_repository.get_by_notify_id(notification.notify_id)
        if existing is not None:
            return {"code": "SUCCESS", "message": "ok"}

        order = self.order_repository.get_by_order_id(order_id=notification.order_id)
        if order is None:
            raise NotFoundError(message="order not found")
        if notification.amount != order.amount:
            raise ValidationError(message="amount mismatch")
        if notification.status != "success":
            raise ValidationError(message="payment not successful")

        self.payment_callback_repository.create(
            notify_id=notification.notify_id,
            order_id=notification.order_id,
            payload=payload,
        )
        if order.status != "paid":
            self.order_repository.mark_paid(order=order, paid_at=notification.paid_at)
            report = self.report_repository.get_for_user(report_id=order.report_id, user_id=order.user_id)
            if report is None:
                raise NotFoundError(message="report not found")
            self.report_repository.mark_generating(report=report)
        self.db.commit()
        return {"code": "SUCCESS", "message": "ok"}
