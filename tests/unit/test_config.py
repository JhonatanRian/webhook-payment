from app.core.config import Settings


def test_private_key_sanitizer() -> None:
    raw_key = "-----BEGIN ECDSA PRIVATE KEY-----\\nMHcCAQEEIBx\\n-----END ECDSA PRIVATE KEY-----"
    settings = Settings(STARK_PRIVATE_KEY=raw_key)
    assert "\\n" not in settings.STARK_PRIVATE_KEY
    assert "\n" in settings.STARK_PRIVATE_KEY
    assert settings.STARK_PRIVATE_KEY.startswith("-----BEGIN ECDSA PRIVATE KEY-----")


def test_tax_id_sanitizer() -> None:
    settings = Settings(TARGET_TAX_ID="20.018.183/0001-80")
    assert settings.TARGET_TAX_ID == "20018183000180"
