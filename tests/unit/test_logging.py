import logging
from unittest.mock import patch

from app.core.config import Settings
from app.core.logging import setup_logging


def test_setup_logging_sandbox() -> None:
    with patch("app.core.logging.settings", Settings(STARK_ENVIRONMENT="sandbox")):
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO


def test_setup_logging_production_json() -> None:
    with patch("app.core.logging.settings", Settings(STARK_ENVIRONMENT="production")):
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
