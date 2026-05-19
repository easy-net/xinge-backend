import logging
import secrets
from datetime import datetime

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.config import get_settings
from app.core.security import decrypt_text
from app.repositories.order_repository import OrderRepository
from app.repositories.product_config_repository import ProductConfigRepository
from app.repositories.report_repository import ReportRepository
from app.services.distributor_service import DistributorService


class OrderService:
    def __init__(self, db, wechat_pay_client, settings=None):
        self.db = db
        self.wechat_pay_client = wechat_pay_client
        self.settings = settings or get_settings()
        self.order_repository = OrderRepository(db)
        self.product_config_repository = ProductConfigRepository(db)
        self.report_repository = ReportRepository(db)

    def create_order(self, *, user, report_id: int, amount: int, platform: str = "android"):
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
            "order.create.start order_id=%s user_id=%s report_id=%s amount=%s openid=%s pay_client=%s platform=%s",
            order_id,
            user.id,
            report_id,
            amount,
            "{}***{}".format(user.openid[:4], user.openid[-4:]) if user.openid and len(user.openid) >= 8 else bool(user.openid),
            type(self.wechat_pay_client).__name__,
            platform,
        )
        payment = self._create_virtual_payment(user=user, order_id=order_id, amount=amount, platform=platform)
        order = self.order_repository.create(
            order_id=order_id,
            user_id=user.id,
            report_id=report_id,
            amount=amount,
            channel="wechat_virtual",
            status="pending",
            prepay_id=payment.outTradeNo,
        )
        self.report_repository.update_status(report=report, status="unpaid")
        self.db.commit()
        logger.info(
            "order.create.success order_id=%s offer_id=%s platform=%s env=%s",
            order.order_id,
            payment.offerId,
            payment.platform,
            payment.env,
        )
        return {
            "amount": order.amount,
            "order_id": order.order_id,
            "payment_provider": "wechat_virtual",
            "payment_debug": {
                "has_mode": bool(payment.mode),
                "has_sign_data": bool(payment.signData),
                "has_pay_sig": bool(payment.paySig),
                "has_signature": bool(payment.signature),
                "offer_id": payment.offerId,
            },
            "payment_params": self._serialize_virtual_payment(payment),
            "virtual_payment_params": self._serialize_virtual_payment(payment),
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

    def repay_order(self, *, user, order_id: str, platform: str = "android"):
        order = self.order_repository.get_for_user(order_id=order_id, user_id=user.id)
        if order is None:
            raise NotFoundError(message="order not found")
        if order.status != "pending":
            raise ConflictError(message="order is not pending")

        payment = self._create_virtual_payment(user=user, order_id=order.order_id, amount=order.amount, platform=platform)
        self.order_repository.update_prepay(order=order, prepay_id=payment.outTradeNo)
        self.db.commit()

        return {
            "amount": order.amount,
            "order_id": order.order_id,
            "payment_provider": "wechat_virtual",
            "payment_debug": {
                "has_mode": bool(payment.mode),
                "has_sign_data": bool(payment.signData),
                "has_pay_sig": bool(payment.paySig),
                "has_signature": bool(payment.signature),
                "offer_id": payment.offerId,
            },
            "payment_params": self._serialize_virtual_payment(payment),
            "virtual_payment_params": self._serialize_virtual_payment(payment),
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

    def _get_user_session_key(self, user) -> str:
        session_key_ciphertext = getattr(user, "session_key_ciphertext", "") or ""
        if not session_key_ciphertext:
            return ""
        return decrypt_text(session_key_ciphertext, self.settings.encryption_key)

    def _create_virtual_payment(self, *, user, order_id: str, amount: int, platform: str):
        return self.wechat_pay_client.create_virtual_prepay(
            order_id=order_id,
            amount=amount,
            openid=user.openid,
            platform=platform,
            session_key=self._get_user_session_key(user),
        )

    def _serialize_virtual_payment(self, payment):
        return {
            "mode": payment.mode,
            "signData": payment.signData,
            "paySig": payment.paySig,
            "signature": payment.signature,
            "offerId": payment.offerId,
            "buyQuantity": payment.buyQuantity,
            "env": payment.env,
            "currencyType": payment.currencyType,
            "platform": payment.platform,
            "productId": payment.productId,
            "goodsPrice": payment.goodsPrice,
            "outTradeNo": payment.outTradeNo,
        }
