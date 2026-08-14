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


def test_resolved_private_key_empty() -> None:
    settings = Settings(STARK_PRIVATE_KEY="", STARK_PRIVATE_KEY_PATH="")
    assert settings.resolved_private_key == ""


def test_tax_id_sanitizer() -> None:
    settings = Settings(TARGET_TAX_ID="20.018.183/0001-80")
    assert settings.TARGET_TAX_ID == "20018183000180"

    assert Settings.sanitize_tax_id(12345) == 12345


def test_scheduler_mode_sanitizer() -> None:
    assert Settings(SCHEDULER_MODE="once").SCHEDULER_MODE == "once"
    assert Settings(SCHEDULER_MODE="RECURRING").SCHEDULER_MODE == "recurring"
    assert Settings(SCHEDULER_MODE="invalid").SCHEDULER_MODE == "once"


def test_scheduler_interval_minutes_sanitizer() -> None:
    assert Settings(SCHEDULER_INTERVAL_MINUTES="60").SCHEDULER_INTERVAL_MINUTES == 60
    assert Settings(SCHEDULER_INTERVAL_MINUTES="-5").SCHEDULER_INTERVAL_MINUTES == 180
    assert Settings(SCHEDULER_INTERVAL_MINUTES="0").SCHEDULER_INTERVAL_MINUTES == 180
    assert Settings(SCHEDULER_INTERVAL_MINUTES="abc").SCHEDULER_INTERVAL_MINUTES == 180


def test_scheduler_max_cycles_sanitizer() -> None:
    assert Settings(SCHEDULER_MAX_CYCLES="12").SCHEDULER_MAX_CYCLES == 12
    assert Settings(SCHEDULER_MAX_CYCLES="1").SCHEDULER_MAX_CYCLES == 1
    assert Settings(SCHEDULER_MAX_CYCLES="0").SCHEDULER_MAX_CYCLES == 8
    assert Settings(SCHEDULER_MAX_CYCLES="-10").SCHEDULER_MAX_CYCLES == 8
    assert Settings(SCHEDULER_MAX_CYCLES="invalid").SCHEDULER_MAX_CYCLES == 8


def test_scheduler_explicit_max_cycles_property() -> None:
    assert Settings(SCHEDULER_MAX_CYCLES=8).max_cycles == 8
    assert Settings(SCHEDULER_MAX_CYCLES=12).max_cycles == 12
    assert Settings(SCHEDULER_MAX_CYCLES=24).max_cycles == 24


def test_scheduler_jobstore_url_sanitizer() -> None:
    s1 = Settings(SCHEDULER_JOBSTORE_URL="sqlite+aiosqlite:///./test.db")
    assert s1.SCHEDULER_JOBSTORE_URL == "sqlite:///./test.db"

    s2 = Settings(SCHEDULER_JOBSTORE_URL="sqlite:///./test.db")
    assert s2.SCHEDULER_JOBSTORE_URL == "sqlite:///./test.db"

    s3 = Settings.model_validate({"SCHEDULER_JOBSTORE_URL": 123})
    assert s3.SCHEDULER_JOBSTORE_URL == "sqlite:///./webhook_payment.db"


def test_log_format_sanitizer() -> None:
    assert Settings(LOG_FORMAT="JSON").LOG_FORMAT == "json"
    assert Settings(LOG_FORMAT="default").LOG_FORMAT == "default"
    assert Settings.model_validate({"LOG_FORMAT": 123}).LOG_FORMAT == "auto"


def test_cors_origins_parsing() -> None:
    assert Settings(CORS_ORIGINS="*").parsed_cors_origins == ["*"]
    assert Settings(
        CORS_ORIGINS="https://app.example.com, http://localhost:5173"
    ).parsed_cors_origins == ["https://app.example.com", "http://localhost:5173"]
    assert Settings.model_validate({"CORS_ORIGINS": None}).parsed_cors_origins == ["*"]
    assert Settings(CORS_ORIGINS="").parsed_cors_origins == ["*"]
