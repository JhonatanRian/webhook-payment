import logging
from functools import lru_cache
from pathlib import Path

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

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "auto"

    @property
    def resolved_private_key(self) -> str:
        if self.STARK_PRIVATE_KEY_PATH:
            key_path = Path(self.STARK_PRIVATE_KEY_PATH).expanduser().resolve()
            if key_path.is_file():
                logger.info("Carregando chave privada a partir de: %s", key_path)
                return key_path.read_text(encoding="utf-8").strip()
            logger.error("Chave não encontrada em STARK_PRIVATE_KEY_PATH: %s", key_path)
            raise FileNotFoundError(
                f"Arquivo de chave privada do Stark Bank não encontrado em: {key_path}"
            )

        if self.STARK_PRIVATE_KEY:
            potential_path = Path(self.STARK_PRIVATE_KEY.strip()).expanduser()
            if potential_path.is_file():
                logger.info("Carregando chave privada a partir de: %s", potential_path)
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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
