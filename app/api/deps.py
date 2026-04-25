from dataclasses import dataclass
from typing import Generator, Optional, Tuple

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.errors import AuthError, NotFoundError, ValidationError
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
    request: Request,
    x_login_code: Optional[str] = Header(None, alias="X-Login-Code"),
    x_system_version: Optional[str] = Header(None, alias="X-System-Version"),
    x_device_uuid: Optional[str] = Header(None, alias="X-Device-UUID"),
) -> MPRequestContext:
    settings = request.app.state.settings
    if settings.unsafe_disable_validation:
        return MPRequestContext(
            login_code=x_login_code or "unsafe-login-code",
            system_version=x_system_version or "unsafe-system-version",
            device_uuid=x_device_uuid or "unsafe-device-uuid",
        )

    missing_headers = []
    if not x_login_code:
        missing_headers.append("X-Login-Code")
    if not x_system_version:
        missing_headers.append("X-System-Version")
    if not x_device_uuid:
        missing_headers.append("X-Device-UUID")
    if missing_headers:
        raise ValidationError(message="missing required headers: {}".format(", ".join(missing_headers)))

    return MPRequestContext(
        login_code=x_login_code,
        system_version=x_system_version,
        device_uuid=x_device_uuid,
    )


def get_current_user(
    request: Request,
    request_context: MPRequestContext = Depends(get_mp_request_context),
    db: Session = Depends(get_db_session),
    wechat_auth_client=Depends(get_wechat_auth_client),
) -> Tuple[User, MPRequestContext]:
    settings = request.app.state.settings
    user_repository = UserRepository(db)

    if settings.unsafe_disable_validation:
        base = request_context.login_code or request_context.device_uuid or "default"
        safe = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in base)[:64] or "default"
        openid = "unsafe-openid-{}".format(safe)
        user = user_repository.get_by_openid(openid)
        if user is None:
            user = user_repository.create_user(openid=openid, unionid="unsafe-unionid-{}".format(safe))
        user_repository.update_device(
            user=user,
            device_uuid=request_context.device_uuid,
            system_version=request_context.system_version,
        )
        db.commit()
        return user, request_context

    session_info = wechat_auth_client.code_to_session(request_context.login_code)
    user = user_repository.get_by_openid(session_info.openid)
    if user is None:
        raise AuthError(message="unauthorized")
    return user, request_context


def get_user_or_404(user_id: int, db: Session) -> User:
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise NotFoundError(message="user not found")
    return user
