"""Configuracao da aplicacao.

Segredos vivem exclusivamente no ambiente do servidor e nunca sao expostos ao
cliente. Ver `.env.example`.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai_api_key: str | None = None
    ai_model: str = "claude-opus-5"
    ai_provider: str | None = None
    cors_origins: str = "http://localhost:3000"

    max_description_length: int = 40_000
    min_description_length: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
