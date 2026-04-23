from app.services.auth_service import AuthService
from tests.fixtures.fakes import FakeWechatAuthClient


class Context:
    login_code = "login-code-user-1"
    system_version = "iOS 17.0"
    device_uuid = "device-1"


def test_login_creates_new_user(db_session):
    service = AuthService(
        db_session,
        FakeWechatAuthClient(session_map={"login-code-user-1": ("openid-user-1", "unionid-user-1")}),
    )

    data, user_info = service.login(Context(), None)

    assert data["is_new_user"] is True
    assert data["user_info"]["open_id"] == "openid-user-1"
    assert user_info["user_id"] > 0


def test_login_reuses_existing_user(db_session):
    service = AuthService(
        db_session,
        FakeWechatAuthClient(session_map={"login-code-user-1": ("openid-user-1", "unionid-user-1")}),
    )
    first_data, first_user_info = service.login(Context(), None)
    second_data, second_user_info = service.login(Context(), None)

    assert first_data["is_new_user"] is True
    assert second_data["is_new_user"] is False
    assert first_user_info["user_id"] == second_user_info["user_id"]

