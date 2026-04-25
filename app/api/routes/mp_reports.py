import logging

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.api.schemas.mp_reports import MPCreateReportReq, MPPageReq, MPReportIDReq
from app.core.errors import NotFoundError
from app.core.response import mp_response
from app.services.report_service import ReportService

router = APIRouter(tags=["mp/reports"])
logger = logging.getLogger(__name__)


def _mask_text(value):
    if not isinstance(value, str) or not value:
        return value
    if len(value) == 1:
        return "*"
    return "{}{}".format(value[:1], "*" * (len(value) - 1))


def _sanitize_report_log_payload(payload):
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if key == "name":
                sanitized[key] = _mask_text(value)
            elif key == "hukou":
                sanitized[key] = "<redacted>"
            elif key == "notes" and isinstance(value, str):
                sanitized[key] = "<redacted:{} chars>".format(len(value))
            else:
                sanitized[key] = _sanitize_report_log_payload(value)
        return sanitized
    if isinstance(payload, list):
        return [_sanitize_report_log_payload(item) for item in payload]
    return payload


def _build_static_report_url(*, report_id: int, mode: str, base_url: str = ""):
    base_url = base_url.rstrip("/")
    path = "/static/report-preview.html?report_id={}&mode={}".format(report_id, mode)
    return "{}{}".format(base_url, path) if base_url else path


def _unsafe_mock_report_links(report_id: int, base_url: str = ""):
    return {
        "expires_in": 3600,
        "full_h5_url": _build_static_report_url(report_id=report_id, mode="full", base_url=base_url),
        "is_paid": True,
        "pdf_url": _build_static_report_url(report_id=report_id, mode="pdf", base_url=base_url),
        "preview_h5_url": _build_static_report_url(report_id=report_id, mode="preview", base_url=base_url),
        "report_id": report_id,
    }


@router.post("/mp/reports", status_code=201)
def create_report(
    body: MPCreateReportReq,
    request: Request,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    payload = body.model_dump()
    settings = request.app.state.settings
    request_id = getattr(request.state, "request_id", "")
    if settings.log_mp_report_payloads:
        logger.info(
            "mp.create_report.request request_id=%s user_id=%s open_id=%s payload=%s",
            request_id,
            user.id,
            user.openid,
            _sanitize_report_log_payload(payload),
        )
    data = ReportService(db).create_report(user=user, payload=payload)
    if settings.log_mp_report_payloads:
        logger.info(
            "mp.create_report.response request_id=%s user_id=%s report_id=%s data=%s",
            request_id,
            user.id,
            data["report_id"],
            _sanitize_report_log_payload(data),
        )
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/reports/list")
def list_reports(
    body: MPPageReq = Body(default_factory=MPPageReq),
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = ReportService(db).list_reports(user=user, page=body.page, page_size=body.page_size)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/reports/detail")
def report_detail(
    body: MPReportIDReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = ReportService(db).detail(user=user, report_id=body.report_id)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/reports/status")
def report_status(
    body: MPReportIDReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = ReportService(db).status(user=user, report_id=body.report_id)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})


@router.post("/mp/reports/links")
def report_links(
    body: MPReportIDReq,
    request: Request,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    base_url = str(request.base_url).rstrip("/")
    try:
        data = ReportService(db).links(user=user, report_id=body.report_id, base_url=base_url)
    except NotFoundError:
        if not request.app.state.settings.unsafe_disable_validation:
            raise
        data = _unsafe_mock_report_links(body.report_id, base_url=base_url)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})
