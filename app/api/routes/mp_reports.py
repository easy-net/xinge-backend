from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session
from app.api.schemas.mp_reports import MPCreateReportReq, MPPageReq, MPReportIDReq
from app.core.response import mp_response
from app.services.report_service import ReportService

router = APIRouter(tags=["mp/reports"])


@router.post("/mp/reports", status_code=201)
def create_report(
    body: MPCreateReportReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = ReportService(db).create_report(user=user, payload=body.model_dump())
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
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    user, _ = current
    data = ReportService(db).links(user=user, report_id=body.report_id)
    return mp_response(data=data, user_info={"open_id": user.openid, "user_id": user.id})
