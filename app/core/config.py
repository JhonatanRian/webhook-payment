import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    STARK_PROJECT_ID: str = "sandbox-project-id"
    STARK_PRIVATE_KEY: str = ""
    STARK_PRIVATE_KEY_PATH: str = ""
    STARK_ENVIRONMENT: str = "sandbox"

    TARGET_BANK_CODE: str = "20018183"
    TARGET_BRANCH: str = "0001"
    TARGET_ACCOUNT: str = "6341320293482496"
    TARGET_NAME: str = "Stark Bank S.A."
    TARGET_TAX_ID: str = "20018183000180"
    TARGET_ACCOUNT_TYPE: str = "payment"

    DATABASE_URL: str = "sqlite+aiosqlite:///./webhook_payment.db"

    CORS_ORIGINS: str = "*"

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "auto"

    SCHEDULER_MODE: Literal["once", "recurring"] = "once"
    SCHEDULER_MAX_CYCLES: int = 8
    SCHEDULER_INTERVAL_MINUTES: int = 180
    SCHEDULER_JOBSTORE_URL: str = "sqlite:///./webhook_payment.db"

    @field_validator("SCHEDULER_JOBSTORE_URL", mode="before")
    @classmethod
    def sanitize_jobstore_url(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.replace("+aiosqlite", "")
        return "sqlite:///./webhook_payment.db"

    @field_validator("SCHEDULER_MODE", mode="before")
    @classmethod
    def sanitize_scheduler_mode(cls, v: Any) -> str:
        if isinstance(v, str):
            v_lower = v.lower().strip()
            if v_lower in ("once", "recurring"):
                return v_lower
        return "once"

    @field_validator("SCHEDULER_MAX_CYCLES", mode="before")
    @classmethod
    def sanitize_scheduler_max_cycles(cls, v: Any) -> int:
        try:
            val = int(v)
            return val if val >= 1 else 8
        except (ValueError, TypeError):
            return 8

    @field_validator("SCHEDULER_INTERVAL_MINUTES", mode="before")
    @classmethod
    def sanitize_scheduler_interval_minutes(cls, v: Any) -> int:
        try:
            val = int(v)
            return val if val >= 1 else 180
        except (ValueError, TypeError):
            return 180

    @property
    def max_cycles(self) -> int:
        return max(1, self.SCHEDULER_MAX_CYCLES)

    @property
    def parsed_cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return origins if origins else ["*"]

    @property
    def resolved_private_key(self) -> str:
        if self.STARK_PRIVATE_KEY_PATH:
            key_path = Path(self.STARK_PRIVATE_KEY_PATH).expanduser().resolve()
            if key_path.is_file():
                logger.info("Loading private key from: %s", key_path)
                return key_path.read_text(encoding="utf-8").strip()
            logger.error("Key not found at STARK_PRIVATE_KEY_PATH: %s", key_path)
            raise FileNotFoundError(f"Stark Bank private key file not found at: {key_path}")

        if self.STARK_PRIVATE_KEY:
            potential_path = Path(self.STARK_PRIVATE_KEY.strip()).expanduser()
            if potential_path.is_file():
                logger.info("Loading private key from: %s", potential_path)
                return potential_path.read_text(encoding="utf-8").strip()

            return self.STARK_PRIVATE_KEY.replace("\\n", "\n").strip()

        return ""

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def sanitize_log_level(cls, v: str) -> str:
        if isinstance(v, str):
            v_upper = v.upper().strip()
            if v_upper in ("DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"):
                return "WARNING" if v_upper == "WARN" else v_upper
        return "INFO"

    @field_validator("LOG_FORMAT", mode="before")
    @classmethod
    def sanitize_log_format(cls, v: str) -> str:
        if isinstance(v, str):
            v_lower = v.lower().strip()
            if v_lower in ("json", "default", "auto"):
                return v_lower
        return "auto"

    @field_validator("TARGET_TAX_ID", mode="before")
    @classmethod
    def sanitize_tax_id(cls, v: str) -> str:
        if isinstance(v, str):
            return v.replace(".", "").replace("/", "").replace("-", "").strip()
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def sanitize_cors_origins(cls, v: Any) -> str:
        if isinstance(v, str) and v.strip():
            return v.strip()
        return "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
