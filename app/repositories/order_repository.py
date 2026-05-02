from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.models.order import Order


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        order_id: str,
        user_id: int,
        report_id: int,
        amount: int,
        channel: str,
        status: str,
        prepay_id: str,
    ) -> Order:
        order = Order(
            order_id=order_id,
            user_id=user_id,
            report_id=report_id,
            amount=amount,
            channel=channel,
            status=status,
            prepay_id=prepay_id,
        )
        self.db.add(order)
        self.db.flush()
        return order

    def get_pending_for_report(self, *, user_id: int, report_id: int):
        stmt = select(Order).where(
            and_(Order.user_id == user_id, Order.report_id == report_id, Order.status == "pending")
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_for_user(self, *, order_id: str, user_id: int):
        stmt = select(Order).where(and_(Order.order_id == order_id, Order.user_id == user_id))
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_user(self, *, user_id: int, page: int, page_size: int):
        stmt = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc(), Order.id.desc())
        total = len(self.db.execute(stmt).scalars().all())
        offset = max(page - 1, 0) * page_size
        items = self.db.execute(stmt.offset(offset).limit(page_size)).scalars().all()
        return items, total

    def get_by_order_id(self, *, order_id: str):
        stmt = select(Order).where(Order.order_id == order_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def latest_for_report(self, *, report_id: int):
        stmt = select(Order).where(Order.report_id == report_id).order_by(Order.created_at.desc(), Order.id.desc()).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def mark_paid(self, *, order: Order, paid_at: str):
        order.status = "paid"
        order.paid_at = paid_at
        self.db.flush()
        return order

    def update_prepay(self, *, order: Order, prepay_id: str):
        order.prepay_id = prepay_id
        self.db.flush()
        return order
