import logging
import secrets

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.repositories.order_repository import OrderRepository
from app.repositories.product_config_repository import ProductConfigRepository
from app.repositories.report_repository import ReportRepository


class OrderService:
    def __init__(self, db, wechat_pay_client):
        self.db = db
        self.wechat_pay_client = wechat_pay_client
        self.order_repository = OrderRepository(db)
        self.product_config_repository = ProductConfigRepository(db)
        self.report_repository = ReportRepository(db)

    def create_order(self, *, user, report_id: int, amount: int):
        report = self.report_repository.get_for_user(report_id=report_id, user_id=user.id)
        if report is None:
            raise NotFoundError(message="report not found")

        config = self.product_config_repository.get_current()
        if config is None:
            raise NotFoundError(message="product config not found")
        if amount != config.current_amount:
            raise ValidationError(message="amount mismatch")

        pending_order = self.order_repository.get_pending_for_report(user_id=user.id, report_id=report_id)
        if pending_order is not None:
            raise ConflictError(message="duplicate pending order")

        order_id = "ORD{}".format(secrets.token_hex(10).upper())
        logger = logging.getLogger(__name__)
        logger.info(
            "order.create.start order_id=%s user_id=%s report_id=%s amount=%s openid=%s pay_client=%s",
            order_id,
            user.id,
            report_id,
            amount,
            "{}***{}".format(user.openid[:4], user.openid[-4:]) if user.openid and len(user.openid) >= 8 else bool(user.openid),
            type(self.wechat_pay_client).__name__,
        )
        payment = self.wechat_pay_client.create_prepay(order_id=order_id, amount=amount, openid=user.openid)
        order = self.order_repository.create(
            order_id=order_id,
            user_id=user.id,
            report_id=report_id,
            amount=amount,
            channel="wechat",
            status="pending",
            prepay_id=payment.prepay_id,
        )
        self.report_repository.update_status(report=report, status="unpaid")
        self.db.commit()
        logger.info(
            "order.create.success order_id=%s prepay_id=%s sign_type=%s package=%s",
            order.order_id,
            payment.prepay_id,
            payment.signType,
            payment.package,
        )
        return {
            "amount": order.amount,
            "order_id": order.order_id,
            "payment_params": {
                "timeStamp": payment.timeStamp,
                "nonceStr": payment.nonceStr,
                "package": payment.package,
                "signType": payment.signType,
                "paySign": payment.paySign,
            },
            "report_id": order.report_id,
        }

    def detail(self, *, user, order_id: str):
        order = self.order_repository.get_for_user(order_id=order_id, user_id=user.id)
        if order is None:
            raise NotFoundError(message="order not found")
        return {
            "amount": order.amount,
            "created_at": order.created_at.isoformat() + "Z",
            "order_id": order.order_id,
            "paid_at": order.paid_at or None,
            "report_id": order.report_id,
            "status": order.status,
        }
