import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.errors import ValidationError


def load_local_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_local_dotenv()


def env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


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
    wechat_transfer_notify_url: str = ""
    wechat_private_key_path: str = ""
    wechat_serial_no: str = ""
    wechat_api_v3_key: str = ""
    wechat_platform_cert_path: str = ""
    wechat_platform_serial_no: str = ""
    wechat_callback_tolerance: int = 300
    wechat_verify_ssl: bool = True
    wechat_ca_bundle_path: str = ""
    wechat_transfer_scene_id: str = "1005"
    wechat_transfer_remark: str = "fenxiaoshangtixian"
    wechat_transfer_user_recv_perception: str = "laowubaochou"
    wechat_transfer_report_primary: str = "xiaoyuanfenxiao"
    wechat_transfer_report_secondary: str = "fenxiaoshangtixian"
    distributor_withdraw_auto_approve_fen: int = 10000
    unsafe_admin_withdraw_approve: bool = False
    auth_token_ttl_seconds: int = 86400
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
            "WECHAT_TRANSFER_NOTIFY_URL": self.wechat_transfer_notify_url or self.wechat_notify_url,
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
        wechat_transfer_notify_url=os.getenv("WECHAT_TRANSFER_NOTIFY_URL", ""),
        wechat_private_key_path=os.getenv("WECHAT_PRIVATE_KEY_PATH", ""),
        wechat_serial_no=os.getenv("WECHAT_SERIAL_NO", ""),
        wechat_api_v3_key=os.getenv("WECHAT_API_V3_KEY", ""),
        wechat_platform_cert_path=os.getenv("WECHAT_PLATFORM_CERT_PATH", ""),
        wechat_platform_serial_no=os.getenv("WECHAT_PLATFORM_SERIAL_NO", ""),
        wechat_callback_tolerance=int(os.getenv("WECHAT_CALLBACK_TOLERANCE", "300")),
        wechat_verify_ssl=os.getenv("WECHAT_VERIFY_SSL", "true").lower() == "true",
        wechat_ca_bundle_path=os.getenv("WECHAT_CA_BUNDLE_PATH", ""),
        wechat_transfer_scene_id=env_or_default("WECHAT_TRANSFER_SCENE_ID", "1005"),
        wechat_transfer_remark=env_or_default("WECHAT_TRANSFER_REMARK", "分销佣金提现"),
        wechat_transfer_user_recv_perception=env_or_default("WECHAT_TRANSFER_USER_RECV_PERCEPTION", "劳务报酬"),
        wechat_transfer_report_primary=env_or_default("WECHAT_TRANSFER_REPORT_PRIMARY", "校园分销"),
        wechat_transfer_report_secondary=env_or_default("WECHAT_TRANSFER_REPORT_SECONDARY", "分销佣金提现"),
        distributor_withdraw_auto_approve_fen=int(os.getenv("DISTRIBUTOR_WITHDRAW_AUTO_APPROVE_FEN", "10000")),
        unsafe_admin_withdraw_approve=os.getenv("UNSAFE_ADMIN_WITHDRAW_APPROVE", "false").lower() == "true",
        auth_token_ttl_seconds=int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "86400")),
        dev_auth_bypass=os.getenv("DEV_AUTH_BYPASS", "false").lower() == "true",
        log_mp_report_payloads=os.getenv("LOG_MP_REPORT_PAYLOADS", "false").lower() == "true",
        log_all_api_payloads=os.getenv("LOG_ALL_API_PAYLOADS", "false").lower() == "true",
        unsafe_disable_validation=os.getenv("UNSAFE_DISABLE_VALIDATION", "false").lower() == "true",
        log_current_user_resolution=os.getenv("LOG_CURRENT_USER_RESOLUTION", "false").lower() == "true",
    )
