from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PaymentCallback(Base):
    __tablename__ = "payment_callbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    notify_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    payload_raw: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verify_status: Mapped[str] = mapped_column(String(32), default="verified", nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

