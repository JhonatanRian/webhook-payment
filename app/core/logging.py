import logging
import logging.config
import sys
from typing import Any

from app.core.config import settings


def setup_logging() -> None:
    """Configures centralized application logging system via dictConfig."""
    is_development = settings.STARK_ENVIRONMENT.lower() in ("sandbox", "development", "local")

    logging_config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": (
                    "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "format": (
                    '{"time": "%(asctime)s", "level": "%(levelname)s", '
                    '"module": "%(name)s", "message": "%(message)s"}'
                ),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default" if is_development else "json",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn.access": {"level": "WARNING"},
            "apscheduler": {"level": "INFO"},
        },
    }

    logging.config.dictConfig(logging_config)
