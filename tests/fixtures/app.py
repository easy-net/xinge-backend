import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.base import Base
from app.main import create_app
from tests.fixtures.fakes import FakeWechatAuthClient, FakeWechatPayClient


@pytest.fixture
def test_settings(tmp_path):
    return Settings(
        app_env="test",
        database_url="sqlite+pysqlite:///{}".format(tmp_path / "test.db"),
        encryption_key="0123456789abcdef0123456789abcdef",
    )


@pytest.fixture
def app(test_settings):
    application = create_app(test_settings)
    Base.metadata.create_all(application.state.engine)
    application.state.wechat_auth_client = FakeWechatAuthClient(
        session_map={
            "login-code-user-1": ("openid-user-1", "unionid-user-1"),
            "login-code-user-2": ("openid-user-2", "unionid-user-2"),
        },
        phone_map={
            "phone-code-user-1": "13800138000",
            "phone-code-user-2": "13900139000",
        },
    )
    application.state.wechat_pay_client = FakeWechatPayClient()
    yield application
    Base.metadata.drop_all(application.state.engine)
    application.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
