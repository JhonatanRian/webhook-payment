import logging

import starkbank

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def setup_starkbank_user(custom_settings: Settings | None = None) -> starkbank.Project | None:
    """Configures global starkbank.user Project instance."""
    cfg = custom_settings or get_settings()
    private_key = cfg.resolved_private_key
    if cfg.STARK_PROJECT_ID and private_key:
        project = starkbank.Project(
            environment=cfg.STARK_ENVIRONMENT,
            id=cfg.STARK_PROJECT_ID,
            private_key=private_key,
        )
        starkbank.user = project
        logger.info("Stark Bank Project successfully configured.")
        return project
    logger.warning("STARK_PROJECT_ID or private key not configured. Stark Bank SDK is inactive.")
    return None
