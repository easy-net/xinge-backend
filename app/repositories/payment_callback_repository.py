import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.payment_callback import PaymentCallback


class PaymentCallbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_notify_id(self, notify_id: str):
        stmt = select(PaymentCallback).where(PaymentCallback.notify_id == notify_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, *, notify_id: str, order_id: str, payload: dict, verify_status: str = "verified"):
        callback = PaymentCallback(
            notify_id=notify_id,
            order_id=order_id,
            payload_raw=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            verify_status=verify_status,
        )
        self.db.add(callback)
        self.db.flush()
        return callback
