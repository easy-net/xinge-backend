from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("mp_users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(32), default="preview", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    form_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    progress_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    fail_stage: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    preview_h5_key: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    full_h5_key: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    pdf_key: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    generated_at: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
