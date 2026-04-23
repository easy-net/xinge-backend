from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductConfig(Base):
    __tablename__ = "product_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    currency: Mapped[str] = mapped_column(String(8), default="CNY", nullable=False)
    current_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    current_amount_display: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    discount_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_limited_time: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    limited_time_end: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    original_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    original_amount_display: Mapped[str] = mapped_column(String(32), nullable=False)
    display_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    display_text: Mapped[str] = mapped_column(String(255), default="", nullable=False)

