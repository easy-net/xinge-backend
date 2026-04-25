import logging
import os
from dataclasses import asdict


def configure_logging(settings) -> None:
    logging.basicConfig(
        level=logging.INFO if settings.app_env == "production" else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_startup_environment(settings, *, wechat_auth_client=None) -> None:
    logger = logging.getLogger(__name__)
    logger.info("startup.settings %s", asdict(settings))
    if wechat_auth_client is not None:
        logger.info("startup.wechat_auth_client %s", wechat_auth_client.__class__.__name__)
    for key, value in sorted(os.environ.items()):
        logger.info("startup.environ %s=%s", key, value)
