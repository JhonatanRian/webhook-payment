import starkbank

from app.core.config import Settings, get_settings


def setup_starkbank_user(custom_settings: Settings | None = None) -> starkbank.Project | None:
    """Configures global starkbank.user Project instance."""
    cfg = custom_settings or get_settings()
    if cfg.STARK_PROJECT_ID and cfg.STARK_PRIVATE_KEY:
        project = starkbank.Project(
            environment=cfg.STARK_ENVIRONMENT,
            id=cfg.STARK_PROJECT_ID,
            private_key=cfg.STARK_PRIVATE_KEY,
        )
        starkbank.user = project
        return project
    return None
