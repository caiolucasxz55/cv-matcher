"""Resolucao do provider de IA a partir do ambiente.

Chaves ficam exclusivamente no servidor e nunca sao expostas ao cliente.
Sem AI_API_KEY, a aplicacao degrada para o provider heuristico e continua
funcionando de ponta a ponta.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.heuristic_provider import HeuristicProvider
from app.ai.provider import AIProvider
from app.config import get_settings


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    settings = get_settings()
    forced = (settings.ai_provider or "").strip().lower()
    api_key = (settings.ai_api_key or "").strip()

    if forced == "heuristic" or not api_key:
        return HeuristicProvider()
    if forced == "gemini":
        return GeminiProvider(api_key=api_key, model=settings.ai_model)
    return AnthropicProvider(api_key=api_key, model=settings.ai_model)


def reset_ai_provider_cache() -> None:
    get_ai_provider.cache_clear()
