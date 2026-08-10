"""Selecao do provider de IA a partir do ambiente."""

from __future__ import annotations

import pytest

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.factory import get_ai_provider, reset_ai_provider_cache
from app.ai.gemini_provider import GeminiProvider
from app.ai.heuristic_provider import HeuristicProvider
from app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_caches(monkeypatch: pytest.MonkeyPatch):
    for var in ("AI_API_KEY", "AI_MODEL", "AI_PROVIDER"):
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    reset_ai_provider_cache()
    yield
    get_settings.cache_clear()
    reset_ai_provider_cache()


def test_sem_api_key_usa_heuristico():
    assert isinstance(get_ai_provider(), HeuristicProvider)


def test_forcar_heuristico_mesmo_com_chave(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_API_KEY", "chave-qualquer")
    monkeypatch.setenv("AI_PROVIDER", "heuristic")
    assert isinstance(get_ai_provider(), HeuristicProvider)


def test_provider_padrao_com_chave_e_anthropic(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_API_KEY", "chave-qualquer")
    assert isinstance(get_ai_provider(), AnthropicProvider)


def test_provider_gemini(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AI_API_KEY", "chave-qualquer")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("AI_MODEL", "gemini-2.5-flash")

    provider = get_ai_provider()

    assert isinstance(provider, GeminiProvider)
    assert provider.name == "gemini"
    assert provider.is_remote is True
