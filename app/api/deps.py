from dataclasses import dataclass
from typing import Generator, Tuple

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.errors import AuthError, NotFoundError
from app.db.models.user import User
from app.repositories.user_repository import UserRepository


@dataclass
class MPRequestContext:
    login_code: str
    system_version: str
    device_uuid: str


def get_db_session(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_wechat_auth_client(request: Request):
    return request.app.state.wechat_auth_client


def get_wechat_pay_client(request: Request):
    return request.app.state.wechat_pay_client


def get_mp_request_context(
    x_login_code: str = Header(..., alias="X-Login-Code"),
    x_system_version: str = Header(..., alias="X-System-Version"),
    x_device_uuid: str = Header(..., alias="X-Device-UUID"),
) -> MPRequestContext:
    return MPRequestContext(
        login_code=x_login_code,
        system_version=x_system_version,
        device_uuid=x_device_uuid,
    )


def get_current_user(
    request_context: MPRequestContext = Depends(get_mp_request_context),
    db: Session = Depends(get_db_session),
    wechat_auth_client=Depends(get_wechat_auth_client),
) -> Tuple[User, MPRequestContext]:
    session_info = wechat_auth_client.code_to_session(request_context.login_code)
    user = UserRepository(db).get_by_openid(session_info.openid)
    if user is None:
        raise AuthError(message="unauthorized")
    return user, request_context


def get_user_or_404(user_id: int, db: Session) -> User:
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise NotFoundError(message="user not found")
    return user
