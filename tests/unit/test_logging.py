import logging

from app.core.config import Settings
from app.core.logging import setup_logging


def test_setup_logging_sandbox() -> None:
    cfg = Settings(STARK_ENVIRONMENT="sandbox", LOG_LEVEL="INFO", LOG_FORMAT="auto")
    setup_logging(custom_settings=cfg)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO


def test_setup_logging_production_json() -> None:
    cfg = Settings(STARK_ENVIRONMENT="production", LOG_LEVEL="INFO", LOG_FORMAT="auto")
    setup_logging(custom_settings=cfg)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO


def test_setup_logging_custom_level_debug() -> None:
    cfg = Settings(LOG_LEVEL="DEBUG")
    setup_logging(custom_settings=cfg)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_setup_logging_custom_level_warning() -> None:
    cfg = Settings(LOG_LEVEL="WARNING")
    setup_logging(custom_settings=cfg)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.WARNING


def test_setup_logging_invalid_level_fallback() -> None:
    cfg = Settings(LOG_LEVEL="INVALID_LEVEL")
    setup_logging(custom_settings=cfg)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO


def test_setup_logging_explicit_json_format() -> None:
    cfg = Settings(STARK_ENVIRONMENT="sandbox", LOG_FORMAT="json")
    setup_logging(custom_settings=cfg)
    root_logger = logging.getLogger()
    assert root_logger.handlers[0].formatter is not None

