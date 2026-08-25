"""Environment-driven backend settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.workflow.schemas import ProviderMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    agent_provider: ProviderMode = "demo"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.4"
    openai_agents_tracing: bool = False
    # NoDecode keeps pydantic-settings from JSON-parsing the raw value so the documented
    # comma-separated form (CORS_ALLOW_ORIGINS=a,b) reaches the validator below.
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
