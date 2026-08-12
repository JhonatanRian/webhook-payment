import starkbank

from app.core.config import Settings
from app.core.starkbank import setup_starkbank_user


def test_setup_starkbank_user_with_valid_settings() -> None:
    private_key, _ = starkbank.key.create()
    custom_settings = Settings(
        STARK_PROJECT_ID="1234567890",
        STARK_PRIVATE_KEY=private_key,
        STARK_ENVIRONMENT="sandbox",
    )
    project = setup_starkbank_user(custom_settings)
    assert project is not None
    assert isinstance(project, starkbank.Project)
    assert starkbank.user == project


def test_setup_starkbank_user_with_missing_key() -> None:
    custom_settings = Settings(
        STARK_PROJECT_ID="",
        STARK_PRIVATE_KEY="",
    )
    project = setup_starkbank_user(custom_settings)
    assert project is None
