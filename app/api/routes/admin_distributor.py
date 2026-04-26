from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.response import public_response
from app.services.distributor_service import DistributorService

router = APIRouter(tags=["admin/distributor"])


@router.get("/admin/distributor/applications")
def admin_list_distributor_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query("", pattern="^(|pending|approved|rejected)$"),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db).admin_list_applications(page=page, page_size=page_size, status=status or None)
    return public_response(data)


@router.post("/admin/distributor/applications/{application_id}/approve")
def admin_approve_distributor_application(
    application_id: str,
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db).admin_approve_application(application_id=application_id)
    return public_response(data)


@router.post("/admin/distributor/applications/{application_id}/reject")
def admin_reject_distributor_application(
    application_id: str,
    body: dict = Body(default_factory=dict),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db).admin_reject_application(
        application_id=application_id,
        reject_reason=str(body.get("reject_reason", "") or ""),
    )
    return public_response(data)
