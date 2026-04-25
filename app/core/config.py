import os
from dataclasses import dataclass
from functools import lru_cache

from app.core.errors import ValidationError


@dataclass
class Settings:
    app_env: str = "development"
    database_url: str = "sqlite+pysqlite:////tmp/xinge.db"
    encryption_key: str = "0123456789abcdef0123456789abcdef"
    allow_ephemeral_db: bool = True
    port: int = 80
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    dev_auth_bypass: bool = False
    log_mp_report_payloads: bool = False
    unsafe_disable_validation: bool = False

    def validate(self) -> None:
        if len(self.encryption_key) < 32:
            raise ValidationError(message="ENCRYPTION_KEY must be at least 32 characters")

        if self.app_env == "production" and self.database_url.startswith("sqlite") and not self.allow_ephemeral_db:
            raise ValidationError(message="production deployment requires a persistent DATABASE_URL")

        if self.app_env == "production" and self.unsafe_disable_validation:
            raise ValidationError(message="UNSAFE_DISABLE_VALIDATION cannot be enabled in production")

        if self.app_env == "production" and not self.dev_auth_bypass:
            if not self.wechat_app_id or not self.wechat_app_secret:
                raise ValidationError(message="WECHAT_APP_ID and WECHAT_APP_SECRET are required in production")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite+pysqlite:////tmp/xinge.db"),
        encryption_key=os.getenv("ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef"),
        allow_ephemeral_db=os.getenv("ALLOW_EPHEMERAL_DB", "true").lower() == "true",
        port=int(os.getenv("PORT", "80")),
        wechat_app_id=os.getenv("WECHAT_APP_ID", ""),
        wechat_app_secret=os.getenv("WECHAT_APP_SECRET", ""),
        dev_auth_bypass=os.getenv("DEV_AUTH_BYPASS", "false").lower() == "true",
        log_mp_report_payloads=os.getenv("LOG_MP_REPORT_PAYLOADS", "false").lower() == "true",
        unsafe_disable_validation=os.getenv("UNSAFE_DISABLE_VALIDATION", "false").lower() == "true",
    )
