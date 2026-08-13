from pathlib import Path

import pytest

from app.core.config import Settings


def test_resolved_private_key_inline_string() -> None:
    raw_key = "-----BEGIN ECDSA PRIVATE KEY-----\\nMHcCAQEEIBx\\n-----END ECDSA PRIVATE KEY-----"
    settings = Settings(STARK_PRIVATE_KEY=raw_key, STARK_PRIVATE_KEY_PATH="")
    resolved = settings.resolved_private_key
    assert "\\n" not in resolved
    assert "\n" in resolved
    assert resolved.startswith("-----BEGIN ECDSA PRIVATE KEY-----")


def test_resolved_private_key_from_key_path(tmp_path: Path) -> None:
    pem_file = tmp_path / "privateKey.pem"
    pem_content = "-----BEGIN ECDSA PRIVATE KEY-----\nSECRET_KEY\n-----END ECDSA PRIVATE KEY-----"
    pem_file.write_text(pem_content, encoding="utf-8")

    settings = Settings(STARK_PRIVATE_KEY_PATH=str(pem_file))
    assert settings.resolved_private_key == pem_content


def test_resolved_private_key_from_stark_private_key_as_path(tmp_path: Path) -> None:
    pem_file = tmp_path / "test_key.pem"
    pem_content = "-----BEGIN ECDSA PRIVATE KEY-----\nFILE_KEY\n-----END ECDSA PRIVATE KEY-----"
    pem_file.write_text(pem_content, encoding="utf-8")

    settings = Settings(STARK_PRIVATE_KEY=str(pem_file), STARK_PRIVATE_KEY_PATH="")
    assert settings.resolved_private_key == pem_content


def test_resolved_private_key_file_not_found(tmp_path: Path) -> None:
    non_existent = tmp_path / "missing.pem"
    settings = Settings(STARK_PRIVATE_KEY_PATH=str(non_existent))
    with pytest.raises(FileNotFoundError):
        _ = settings.resolved_private_key


def test_tax_id_sanitizer() -> None:
    settings = Settings(TARGET_TAX_ID="20.018.183/0001-80")
    assert settings.TARGET_TAX_ID == "20018183000180"

