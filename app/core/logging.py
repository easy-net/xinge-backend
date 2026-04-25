import logging
import os
from dataclasses import asdict


def configure_logging(settings) -> None:
    logging.basicConfig(
        level=logging.INFO if settings.app_env == "production" else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def log_startup_environment(settings) -> None:
    logger = logging.getLogger(__name__)
    logger.info("startup.settings %s", asdict(settings))
    logger.info("startup.environ %s", dict(sorted(os.environ.items())))
