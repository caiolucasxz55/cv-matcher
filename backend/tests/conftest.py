from __future__ import annotations

import pytest

from app.config import Settings
from app.resume import skills_store

# Os testes nunca devem ler o `.env` real (pode conter uma chave de IA de
# verdade) — senao a suite vira dependente de rede e nao-deterministica.
# Precisa rodar na importacao do conftest, antes de qualquer modulo chamar
# `get_settings()` no escopo do modulo (ex.: `app/routers/adapt.py`).
Settings.model_config["env_file"] = None


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def _isolate_custom_skills(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Evita que testes leiam/escrevam o `data/custom_skills.json` real."""
    monkeypatch.setenv("CUSTOM_SKILLS_PATH", str(tmp_path / "custom_skills.json"))
    skills_store.reset_cache()
    yield
    skills_store.reset_cache()
