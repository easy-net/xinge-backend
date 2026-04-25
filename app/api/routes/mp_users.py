from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db_session, get_mp_request_context, get_wechat_auth_client
from app.api.schemas.mp_users import MPUpdateMeReq
from app.core.response import mp_response
from app.services.auth_service import AuthService

router = APIRouter(tags=["mp/users"])


@router.post("/mp/users/me")
def me(
    request: Request,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_auth_client=Depends(get_wechat_auth_client),
):
    user, request_context = current
    data, user_info = AuthService(db, wechat_auth_client, request.app.state.settings).me(user, request_context)
    return mp_response(data=data, user_info=user_info)


@router.post("/mp/users/me/update")
def update_me(
    request: Request,
    body: MPUpdateMeReq,
    current=Depends(get_current_user),
    db: Session = Depends(get_db_session),
    wechat_auth_client=Depends(get_wechat_auth_client),
):
    user, request_context = current
    data, user_info = AuthService(db, wechat_auth_client, request.app.state.settings).update_me(
        user,
        request_context,
        nickname=body.nickname,
        avatar_url=body.avatar_url,
    )
    return mp_response(data=data, user_info=user_info)
