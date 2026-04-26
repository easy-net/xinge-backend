from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.report import Report


class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, *, user_id: int, name: str, form_data: dict, report_type: str = "preview", status: str = "draft") -> Report:
        report = Report(
            user_id=user_id,
            name=name,
            form_data=form_data,
            report_type=report_type,
            status=status,
        )
        self.db.add(report)
        self.db.flush()
        return report

    def count_for_user(self, user_id: int) -> int:
        stmt = select(func.count(Report.id)).where(Report.user_id == user_id)
        return self.db.execute(stmt).scalar_one()

    def stats_for_user(self, user_id: int) -> dict:
        total = self.count_for_user(user_id)
        paid_stmt = select(func.count(Report.id)).where(
            Report.user_id == user_id,
            Report.status.in_(("paid", "collecting", "planning", "generating", "analyzing", "completed")),
        )
        paid_count = self.db.execute(paid_stmt).scalar_one()
        return {
            "paid_count": paid_count,
            "total_count": total,
            "unpaid_count": max(total - paid_count, 0),
        }

    def list_for_user(self, *, user_id: int, page: int, page_size: int):
        total_stmt = select(func.count(Report.id)).where(Report.user_id == user_id)
        total = self.db.execute(total_stmt).scalar_one()
        stmt = (
            select(Report)
            .where(Report.user_id == user_id)
            .order_by(Report.created_at.desc(), Report.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = self.db.execute(stmt).scalars().all()
        return items, total

    def get_for_user(self, *, report_id: int, user_id: int):
        stmt = select(Report).where(Report.id == report_id, Report.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def update_status(self, *, report: Report, status: str):
        report.status = status
        self.db.flush()
        return report

    def mark_generating(self, *, report: Report):
        report.status = "generating"
        report.progress_json = {
            "completion_rate": 0.4,
            "current_stage": "generating",
            "done_steps": 4,
            "total_steps": 10,
        }
        self.db.flush()
        return report

    def mark_completed(self, *, report: Report, generated_at: str):
        report.status = "completed"
        report.progress_json = {
            "completion_rate": 1.0,
            "current_stage": "completed",
            "done_steps": 10,
            "total_steps": 10,
        }
        report.preview_h5_key = report.preview_h5_key or "h5/{}_preview.html".format(report.id)
        report.full_h5_key = report.full_h5_key or "h5/{}_full.html".format(report.id)
        report.pdf_key = report.pdf_key or "pdf/{}.pdf".format(report.id)
        report.generated_at = generated_at
        self.db.flush()
        return report
