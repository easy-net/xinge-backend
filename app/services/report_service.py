from datetime import datetime

from app.repositories.order_repository import OrderRepository
from app.core.errors import NotFoundError
from app.repositories.report_repository import ReportRepository


class ReportService:
    def __init__(self, db):
        self.db = db
        self.repository = ReportRepository(db)
        self.order_repository = OrderRepository(db)

    def create_report(self, *, user, payload: dict):
        report = self.repository.create(user_id=user.id, name=payload["name"], form_data=payload)
        self.db.commit()
        return {
            "created_at": report.created_at.isoformat() + "Z",
            "name": report.name,
            "report_id": report.id,
            "report_type": report.report_type,
            "status": report.status,
        }

    def list_reports(self, *, user, page: int, page_size: int):
        reports, total = self.repository.list_for_user(user_id=user.id, page=page, page_size=page_size)
        return {
            "list": [
                self._serialize_list_item(report)
                for report in reports
            ],
            "page": page,
            "page_size": page_size,
            "page_total": (total + page_size - 1) // page_size if page_size else 0,
            "total": total,
        }

    def detail(self, *, user, report_id: int):
        report = self.repository.get_for_user(report_id=report_id, user_id=user.id)
        if report is None:
            raise NotFoundError(message="report not found")
        latest_order = self.order_repository.latest_for_report(report_id=report.id)
        return {
            "report_id": report.id,
            "status": report.status,
            "report_type": report.report_type,
            "is_paid": bool(latest_order and latest_order.status == "paid"),
            "order_id": latest_order.order_id if latest_order else None,
            "order_status": latest_order.status if latest_order else None,
            "form": report.form_data,
            "created_at": report.created_at.isoformat() + "Z",
            "updated_at": report.updated_at.isoformat() + "Z",
        }

    def status(self, *, user, report_id: int):
        report = self.repository.get_for_user(report_id=report_id, user_id=user.id)
        if report is None:
            raise NotFoundError(message="report not found")
        if report.status == "generating":
            self.repository.mark_completed(report=report, generated_at=datetime.utcnow().isoformat() + "Z")
            self.db.commit()
        return {
            "fail_stage": report.fail_stage or None,
            "progress": report.progress_json or {
                "completion_rate": 0.0,
                "current_stage": report.status,
                "done_steps": 0,
                "total_steps": 10,
            },
            "report_id": report.id,
            "report_type": report.report_type,
            "status": report.status,
        }

    def links(self, *, user, report_id: int):
        report = self.repository.get_for_user(report_id=report_id, user_id=user.id)
        if report is None:
            raise NotFoundError(message="report not found")
        latest_order = self.order_repository.latest_for_report(report_id=report.id)
        is_paid = bool(latest_order and latest_order.status == "paid")
        preview_key = report.preview_h5_key or "h5/{}_preview.html".format(report.id)
        preview_url = self._sign_cos_url(preview_key)
        full_url = self._sign_cos_url(report.full_h5_key) if is_paid and report.full_h5_key else None
        pdf_url = self._sign_cos_url(report.pdf_key) if is_paid and report.pdf_key else None
        return {
            "expires_in": 3600,
            "full_h5_url": full_url,
            "is_paid": is_paid,
            "pdf_url": pdf_url,
            "preview_h5_url": preview_url,
            "report_id": report.id,
        }

    def _serialize_list_item(self, report):
        latest_order = self.order_repository.latest_for_report(report_id=report.id)
        return {
            "created_at": report.created_at.isoformat() + "Z",
            "fail_stage": report.fail_stage or None,
            "is_paid": bool(latest_order and latest_order.status == "paid"),
            "name": report.name,
            "order_id": latest_order.order_id if latest_order else None,
            "order_status": latest_order.status if latest_order else None,
            "paid_at": latest_order.paid_at if latest_order else None,
            "report_id": report.id,
            "report_type": report.report_type,
            "school_name": report.form_data.get("school_name"),
            "status": report.status,
            "updated_at": report.updated_at.isoformat() + "Z",
        }

    def _sign_cos_url(self, key: str):
        return "https://cos.example.com/{}?sign=mock-signature".format(key)
