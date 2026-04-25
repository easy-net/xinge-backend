import pytest

from app.core.config import Settings
from app.core.errors import ValidationError


def test_settings_reject_short_encryption_key():
    settings = Settings(encryption_key="short")
    with pytest.raises(ValidationError):
        settings.validate()


def test_production_settings_require_persistent_db_when_ephemeral_disabled():
    settings = Settings(
        app_env="production",
        database_url="sqlite+pysqlite:////tmp/xinge.db",
        encryption_key="0123456789abcdef0123456789abcdef",
        allow_ephemeral_db=False,
    )
    with pytest.raises(ValidationError):
        settings.validate()


def test_production_settings_reject_unsafe_disable_validation():
    settings = Settings(
        app_env="production",
        database_url="mysql+pymysql://root:password@mysql:3306/xinge_backend",
        encryption_key="0123456789abcdef0123456789abcdef",
        allow_ephemeral_db=False,
        wechat_app_id="wx-app-id",
        wechat_app_secret="wx-app-secret",
        unsafe_disable_validation=True,
    )
    with pytest.raises(ValidationError):
        settings.validate()
