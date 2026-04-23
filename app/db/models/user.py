from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "mp_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    unionid: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    nickname: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    phone_ciphertext: Mapped[str] = mapped_column(String(2048), default="", nullable=False)
    phone_masked: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    is_distributor: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    devices = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")

