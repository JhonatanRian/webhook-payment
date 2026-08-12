from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    STARK_PROJECT_ID: str = "sandbox-project-id"
    STARK_PRIVATE_KEY: str = ""
    STARK_ENVIRONMENT: str = "sandbox"

    TARGET_BANK_CODE: str = "20018183"
    TARGET_BRANCH: str = "0001"
    TARGET_ACCOUNT: str = "6341320293482496"
    TARGET_NAME: str = "Stark Bank S.A."
    TARGET_TAX_ID: str = "20018183000180"
    TARGET_ACCOUNT_TYPE: str = "payment"

    DATABASE_URL: str = "sqlite+aiosqlite:///./webhook_payment.db"

    @field_validator("STARK_PRIVATE_KEY", mode="before")
    @classmethod
    def sanitize_private_key(cls, v: str) -> str:
        if isinstance(v, str):
            return v.replace("\\n", "\n").strip()
        return v

    @field_validator("TARGET_TAX_ID", mode="before")
    @classmethod
    def sanitize_tax_id(cls, v: str) -> str:
        if isinstance(v, str):
            # Strip punctuation like . / -
            return v.replace(".", "").replace("/", "").replace("-", "").strip()
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
