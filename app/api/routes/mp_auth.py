from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session, get_mp_request_context, get_wechat_auth_client
from app.api.schemas.mp_auth import MPBindPhoneReq, MPLoginReq
from app.core.response import mp_response
from app.services.auth_service import AuthService

router = APIRouter(tags=["mp/auth"])


@router.post("/mp/auth/login")
def mp_login(
    request: Request,
    body: MPLoginReq = Body(default_factory=MPLoginReq),
    request_context=Depends(get_mp_request_context),
    db: Session = Depends(get_db_session),
    wechat_auth_client=Depends(get_wechat_auth_client),
):
    data, user_info = AuthService(db, wechat_auth_client, request.app.state.settings).login(request_context, body.distributor_id)
    return mp_response(data=data, user_info=user_info)


@router.post("/mp/auth/bind-phone")
def bind_phone(
    body: MPBindPhoneReq,
    request: Request,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_auth_client=Depends(get_wechat_auth_client),
):
    user, request_context = current
    data, user_info = AuthService(db, wechat_auth_client, request.app.state.settings).bind_phone(
        user=user,
        request_context=request_context,
        phone_code=body.phone_code,
    )
    return mp_response(data=data, user_info=user_info)
