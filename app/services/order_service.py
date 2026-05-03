import logging
import secrets
from datetime import datetime

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.repositories.order_repository import OrderRepository
from app.repositories.product_config_repository import ProductConfigRepository
from app.repositories.report_repository import ReportRepository
from app.services.distributor_service import DistributorService


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

    def list_orders(self, *, user, page: int, page_size: int):
        orders, total = self.order_repository.list_for_user(user_id=user.id, page=page, page_size=page_size)
        return {
            "list": [self._serialize_order_list_item(order) for order in orders],
            "page": page,
            "page_size": page_size,
            "page_total": (total + page_size - 1) // page_size if page_size else 0,
            "total": total,
        }

    def repay_order(self, *, user, order_id: str):
        order = self.order_repository.get_for_user(order_id=order_id, user_id=user.id)
        if order is None:
            raise NotFoundError(message="order not found")
        if order.status != "pending":
            raise ConflictError(message="order is not pending")

        payment = self.wechat_pay_client.create_prepay(order_id=order.order_id, amount=order.amount, openid=user.openid)
        self.order_repository.update_prepay(order=order, prepay_id=payment.prepay_id)
        self.db.commit()

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

    def confirm_paid(self, *, user, order_id: str, paid_at: str = ""):
        order = self.order_repository.get_for_user(order_id=order_id, user_id=user.id)
        if order is None:
            raise NotFoundError(message="order not found")

        if order.status != "paid":
            normalized_paid_at = paid_at or datetime.utcnow().isoformat() + "Z"
            self.order_repository.mark_paid(order=order, paid_at=normalized_paid_at)
            report = self.report_repository.get_for_user(report_id=order.report_id, user_id=user.id)
            if report is None:
                raise NotFoundError(message="report not found")
            self.report_repository.mark_generating(report=report)

        DistributorService(self.db, self.wechat_pay_client).settle_order_commissions(
            buyer_user=user,
            order=order,
        )
        self.db.commit()

        return {
            "amount": order.amount,
            "order_id": order.order_id,
            "paid_at": order.paid_at,
            "report_id": order.report_id,
            "status": order.status,
        }

    def _serialize_order_list_item(self, order):
        report = self.report_repository.get_for_user(report_id=order.report_id, user_id=order.user_id)
        return {
            "amount": order.amount,
            "created_at": order.created_at.isoformat() + "Z",
            "name": report.name if report else "",
            "order_id": order.order_id,
            "paid_at": order.paid_at or None,
            "report_id": order.report_id,
            "report_type": report.report_type if report else "preview",
            "school_name": (report.form_data or {}).get("school_name") if report else "",
            "status": order.status,
        }
