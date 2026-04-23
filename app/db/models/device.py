from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserDevice(Base):
    __tablename__ = "mp_user_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("mp_users.id"), nullable=False, index=True)
    device_uuid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    system_version: Mapped[str] = mapped_column(String(128), nullable=False)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_ip: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    user = relationship("User", back_populates="devices")

