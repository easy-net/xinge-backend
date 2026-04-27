import logging
import os
from dataclasses import asdict

ESSENTIAL_ENV_KEYS = (
    "APP_ENV",
    "ALLOW_EPHEMERAL_DB",
    "PAYMENT_MODE",
    "PORT",
    "SEED_SCHOOL_FIXTURES_ON_STARTUP",
    "WECHAT_APP_ID",
    "WECHAT_MCH_ID",
    "WECHAT_NOTIFY_URL",
    "WECHAT_TRANSFER_NOTIFY_URL",
    "WECHAT_PRIVATE_KEY_PATH",
    "WECHAT_PLATFORM_CERT_PATH",
)


def configure_logging(settings) -> None:
    logging.basicConfig(
        level=logging.INFO if settings.app_env == "production" else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_startup_environment(settings, *, wechat_auth_client=None) -> None:
    logger = logging.getLogger(__name__)
    is_vercel = os.getenv("VERCEL") == "1"
    verbose = not (settings.app_env == "production" or is_vercel)
    logger.info("startup.settings %s", asdict(settings) if verbose else {
        "app_env": settings.app_env,
        "database_url": settings.database_url,
        "payment_mode": settings.payment_mode,
        "seed_school_fixtures_on_startup": settings.seed_school_fixtures_on_startup,
        "wechat_app_id_present": bool(settings.wechat_app_id),
        "wechat_app_secret_present": bool(settings.wechat_app_secret),
        "wechat_private_key_path": settings.wechat_private_key_path,
        "wechat_platform_cert_path": settings.wechat_platform_cert_path,
    })
    if wechat_auth_client is not None:
        logger.info("startup.wechat_auth_client %s", wechat_auth_client.__class__.__name__)
    environment_items = sorted(os.environ.items()) if verbose else [
        (key, os.getenv(key, "")) for key in ESSENTIAL_ENV_KEYS
    ]
    for key, value in environment_items:
        logger.info("startup.environ %s=%s", key, value)
