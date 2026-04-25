from datetime import datetime
from urllib.parse import urlencode

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

    def links(self, *, user, report_id: int, base_url: str = ""):
        report = self.repository.get_for_user(report_id=report_id, user_id=user.id)
        if report is None:
            raise NotFoundError(message="report not found")
        latest_order = self.order_repository.latest_for_report(report_id=report.id)
        is_paid = bool(latest_order and latest_order.status == "paid")
        preview_url = self._build_report_page_url(
            report_id=report.id,
            mode="preview",
            base_url=base_url,
        )
        full_url = self._build_report_page_url(
            report_id=report.id,
            mode="full",
            base_url=base_url,
        ) if is_paid else None
        pdf_url = self._build_report_page_url(
            report_id=report.id,
            mode="pdf",
            base_url=base_url,
        ) if is_paid else None
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

    def _build_report_page_url(self, *, report_id: int, mode: str, base_url: str = ""):
        query = urlencode({"report_id": report_id, "mode": mode})
        base_url = base_url.rstrip("/")
        path = "/static/report-preview.html?{}".format(query)
        return "{}{}".format(base_url, path) if base_url else path
