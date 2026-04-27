from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.response import public_response
from app.services.admin_user_service import AdminUserService

router = APIRouter(tags=["admin/users"])


@router.get("/admin/users")
def admin_list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str = Query(""),
    role: str = Query("", pattern="^(|user|distributor|admin)$"),
    db: Session = Depends(get_db_session),
):
    data = AdminUserService(db, request.app.state.settings).list_users(
        page=page,
        page_size=page_size,
        keyword=keyword,
        role=role or None,
    )
    return public_response(data)


@router.post("/admin/users")
def admin_create_user(
    request: Request,
    body: dict = Body(default_factory=dict),
    db: Session = Depends(get_db_session),
):
    data = AdminUserService(db, request.app.state.settings).create_user(
        openid=str(body.get("openid", "") or ""),
        unionid=str(body.get("unionid", "") or ""),
        nickname=str(body.get("nickname", "") or ""),
        phone_masked=str(body.get("phone_masked", "") or ""),
        role=str(body.get("role", "user") or "user"),
        distributor_level=str(body.get("distributor_level", "") or ""),
        parent_distributor_id=int(body.get("parent_distributor_id", 0) or 0),
        quota_total=int(body.get("quota_total", 0) or 0),
    )
    return public_response(data)


@router.post("/admin/users/{user_id}/delete")
def admin_delete_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db_session),
):
    data = AdminUserService(db, request.app.state.settings).delete_user(user_id=user_id)
    return public_response(data)
