import logging
import logging.config
import sys
from typing import Any

from app.core.config import Settings, get_settings


def setup_logging(custom_settings: Settings | None = None) -> None:
    """Configures centralized application logging system via dictConfig."""
    cfg = custom_settings or get_settings()
    is_development = cfg.STARK_ENVIRONMENT.lower() in ("sandbox", "development", "local")

    if cfg.LOG_FORMAT == "json":
        formatter_name = "json"
    elif cfg.LOG_FORMAT == "default":
        formatter_name = "default"
    else:
        formatter_name = "default" if is_development else "json"

    log_level = cfg.LOG_LEVEL.upper()

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
                "formatter": formatter_name,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
        "loggers": {
            "uvicorn.access": {"level": "WARNING"},
            "apscheduler": {"level": log_level},
        },
    }

    logging.config.dictConfig(logging_config)
