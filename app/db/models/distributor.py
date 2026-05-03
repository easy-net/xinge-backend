from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DistributorProfile(Base):
    __tablename__ = "distributor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("mp_users.id"), unique=True, index=True, nullable=False)
    distributor_level: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_distributor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    quota_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quota_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_commission: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_sales_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_withdrawn_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unsettled_commission: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="distributor_profile")


class DistributorApplication(Base):
    __tablename__ = "distributor_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("mp_users.id"), index=True, nullable=False)
    real_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    target_level: Mapped[str] = mapped_column(String(32), nullable=False)
    reject_reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="distributor_applications")


class DistributorWithdrawal(Base):
    __tablename__ = "distributor_withdrawals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    withdraw_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("mp_users.id"), index=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    account_name: Mapped[str] = mapped_column(String(128), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(128), nullable=False)
    bank_account_masked: Mapped[str] = mapped_column(String(32), nullable=False)
    transfer_bill_no: Mapped[str] = mapped_column(String(64), default="", index=True, nullable=False)
    fail_reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="distributor_withdrawals")


class DistributorWithdrawalEvent(Base):
    __tablename__ = "distributor_withdrawal_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    withdraw_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    detail: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    operator: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DistributorQuotaRecord(Base):
    __tablename__ = "distributor_quota_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("mp_users.id"), index=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    counterparty_user_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    counterparty_level: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    quota_before: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quota_after: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    remark: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DistributorCommission(Base):
    __tablename__ = "distributor_commissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commission_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    beneficiary_user_id: Mapped[int] = mapped_column(ForeignKey("mp_users.id"), index=True, nullable=False)
    source_user_id: Mapped[int] = mapped_column(ForeignKey("mp_users.id"), index=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    distributor_level: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    rate_bps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    order_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="earned", nullable=False)
    remark: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
