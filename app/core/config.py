import os
from dataclasses import dataclass
from functools import lru_cache

from app.core.errors import ValidationError

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    app_env: str = "development"
    database_url: str = "sqlite+pysqlite:////tmp/xinge.db"
    encryption_key: str = "0123456789abcdef0123456789abcdef"
    allow_ephemeral_db: bool = True
    port: int = 80
    payment_mode: str = "mock"
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_mch_id: str = ""
    wechat_notify_url: str = ""
    wechat_private_key_path: str = ""
    wechat_serial_no: str = ""
    wechat_api_v3_key: str = ""
    wechat_platform_cert_path: str = ""
    wechat_platform_serial_no: str = ""
    wechat_callback_tolerance: int = 300
    dev_auth_bypass: bool = False
    log_mp_report_payloads: bool = False
    log_all_api_payloads: bool = False
    unsafe_disable_validation: bool = False
    log_current_user_resolution: bool = False

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

        if self.app_env == "production" and self.payment_mode == "real":
            missing = self.missing_real_payment_fields()
            if missing:
                raise ValidationError(message="missing real payment settings: {}".format(", ".join(missing)))

    def missing_real_payment_fields(self):
        fields = {
            "WECHAT_APP_ID": self.wechat_app_id,
            "WECHAT_MCH_ID": self.wechat_mch_id,
            "WECHAT_NOTIFY_URL": self.wechat_notify_url,
            "WECHAT_PRIVATE_KEY_PATH": self.wechat_private_key_path,
            "WECHAT_SERIAL_NO": self.wechat_serial_no,
            "WECHAT_API_V3_KEY": self.wechat_api_v3_key,
            "WECHAT_PLATFORM_CERT_PATH": self.wechat_platform_cert_path,
        }
        return [key for key, value in fields.items() if not value]

    def is_real_payment_ready(self) -> bool:
        return self.payment_mode == "real" and not self.missing_real_payment_fields()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite+pysqlite:////tmp/xinge.db"),
        encryption_key=os.getenv("ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef"),
        allow_ephemeral_db=os.getenv("ALLOW_EPHEMERAL_DB", "true").lower() == "true",
        port=int(os.getenv("PORT", "80")),
        payment_mode=os.getenv("PAYMENT_MODE", "mock").strip().lower(),
        wechat_app_id=os.getenv("WECHAT_APP_ID", ""),
        wechat_app_secret=os.getenv("WECHAT_APP_SECRET", ""),
        wechat_mch_id=os.getenv("WECHAT_MCH_ID", ""),
        wechat_notify_url=os.getenv("WECHAT_NOTIFY_URL", ""),
        wechat_private_key_path=os.getenv("WECHAT_PRIVATE_KEY_PATH", ""),
        wechat_serial_no=os.getenv("WECHAT_SERIAL_NO", ""),
        wechat_api_v3_key=os.getenv("WECHAT_API_V3_KEY", ""),
        wechat_platform_cert_path=os.getenv("WECHAT_PLATFORM_CERT_PATH", ""),
        wechat_platform_serial_no=os.getenv("WECHAT_PLATFORM_SERIAL_NO", ""),
        wechat_callback_tolerance=int(os.getenv("WECHAT_CALLBACK_TOLERANCE", "300")),
        dev_auth_bypass=os.getenv("DEV_AUTH_BYPASS", "false").lower() == "true",
        log_mp_report_payloads=os.getenv("LOG_MP_REPORT_PAYLOADS", "false").lower() == "true",
        log_all_api_payloads=os.getenv("LOG_ALL_API_PAYLOADS", "false").lower() == "true",
        unsafe_disable_validation=os.getenv("UNSAFE_DISABLE_VALIDATION", "false").lower() == "true",
        log_current_user_resolution=os.getenv("LOG_CURRENT_USER_RESOLUTION", "false").lower() == "true",
    )
