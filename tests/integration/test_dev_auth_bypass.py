from app.core.config import Settings
from app.main import create_app


def test_create_app_uses_dev_auth_bypass():
    settings = Settings(
        app_env="development",
        database_url="sqlite+pysqlite:////tmp/test-auth-bypass.db",
        encryption_key="0123456789abcdef0123456789abcdef",
        allow_ephemeral_db=True,
        dev_auth_bypass=True,
    )
    app = create_app(settings)
    session = app.state.wechat_auth_client.code_to_session("hello-123")
    assert session.openid == "dev-openid-hello-123"
