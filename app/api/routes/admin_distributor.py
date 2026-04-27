from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.response import public_response
from app.services.distributor_service import DistributorService

router = APIRouter(tags=["admin/distributor"])


@router.get("/admin/distributor/applications")
def admin_list_distributor_applications(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query("", pattern="^(|pending|approved|rejected)$"),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_list_applications(page=page, page_size=page_size, status=status or None)
    return public_response(data)


@router.get("/admin/distributor/users")
def admin_list_distributor_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: str = Query("", pattern="^(|strategic|city|campus)$"),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_list_distributors(page=page, page_size=page_size, level=level or None)
    return public_response(data)


@router.get("/admin/distributor/candidates")
def admin_list_assignable_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str = Query(""),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_list_assignable_users(
        page=page,
        page_size=page_size,
        keyword=keyword,
    )
    return public_response(data)


@router.get("/admin/distributor/users/{user_id}/downlines")
def admin_list_distributor_user_downlines(
    request: Request,
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: str = Query("", pattern="^(|strategic|city|campus)$"),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_list_distributor_downlines(
        user_id=user_id,
        page=page,
        page_size=page_size,
        level=level or None,
    )
    return public_response(data)


@router.post("/admin/distributor/users/{user_id}/downlines/assign")
def admin_assign_distributor_downline(
    request: Request,
    user_id: int,
    body: dict = Body(default_factory=dict),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_assign_downline(
        user_id=user_id,
        downline_user_id=int(body.get("downline_user_id", 0)),
        distributor_level=str(body.get("distributor_level", "") or ""),
    )
    return public_response(data)


@router.post("/admin/distributor/users/{user_id}/downlines/unassign")
def admin_unassign_distributor_downline(
    request: Request,
    user_id: int,
    body: dict = Body(default_factory=dict),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_unassign_downline(
        user_id=user_id,
        downline_user_id=int(body.get("downline_user_id", 0)),
    )
    return public_response(data)


@router.post("/admin/distributor/applications/{application_id}/approve")
def admin_approve_distributor_application(
    request: Request,
    application_id: str,
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_approve_application(application_id=application_id)
    return public_response(data)


@router.post("/admin/distributor/applications/{application_id}/reject")
def admin_reject_distributor_application(
    request: Request,
    application_id: str,
    body: dict = Body(default_factory=dict),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_reject_application(
        application_id=application_id,
        reject_reason=str(body.get("reject_reason", "") or ""),
    )
    return public_response(data)


@router.post("/admin/distributor/users/{user_id}/quota/allocate")
def admin_allocate_distributor_quota(
    request: Request,
    user_id: int,
    body: dict = Body(default_factory=dict),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_allocate_quota(
        user_id=user_id,
        downline_user_id=int(body.get("downline_user_id", 0)),
        amount=int(body.get("amount", 0)),
    )
    return public_response(data)


@router.post("/admin/distributor/users/{user_id}/seed-quota-records")
def admin_seed_distributor_quota_records(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_seed_quota_records(user_id=user_id)
    return public_response(data)


@router.get("/admin/distributor/withdrawals")
def admin_list_distributor_withdrawals(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query("", pattern="^(|pending_review|processing|paid|rejected|failed)$"),
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_list_withdrawals(
        page=page,
        page_size=page_size,
        status=status or None,
    )
    return public_response(data)


@router.post("/admin/distributor/withdrawals/{withdraw_id}/approve")
def admin_approve_distributor_withdrawal(
    request: Request,
    withdraw_id: str,
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_approve_withdrawal(
        withdraw_id=withdraw_id
    )
    return public_response(data)


@router.post("/admin/distributor/withdrawals/{withdraw_id}/reject")
def admin_reject_distributor_withdrawal(
    request: Request,
    withdraw_id: str,
    db: Session = Depends(get_db_session),
):
    data = DistributorService(db, request.app.state.wechat_pay_client, request.app.state.settings).admin_reject_withdrawal(
        withdraw_id=withdraw_id
    )
    return public_response(data)
