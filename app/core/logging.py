import logging


def configure_logging(settings) -> None:
    logging.basicConfig(
        level=logging.INFO if settings.app_env == "production" else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

