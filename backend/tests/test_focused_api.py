"""Testes HTTP do endpoint POST /api/focused/versions — "CV Matcher Novo"."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.resume.adapt import reset_version_counter
from app.resume.focused_adapt import MAX_SECONDARY_ITEMS
from app.versions import clear_versions
from tests.fixtures import BACKEND_PYTHON_JOB

client = TestClient(app)


def _reset_state():
    reset_version_counter()
    clear_versions()


def test_versao_focada_curva_habilidades_pela_categoria_dominante():
    _reset_state()
    response = client.post("/api/focused/versions", json={"description": BACKEND_PYTHON_JOB})
    assert response.status_code == 200
    payload = response.json()

    categories = payload["balanced"]["resume"]["skill_categories"]
    assert categories[0]["id"] == "skills-backend"
    frontend = next(c for c in categories if c["id"] == "skills-frontend")
    assert len(frontend["items"]) <= MAX_SECONDARY_ITEMS


def test_difere_da_versao_oficial_que_nunca_corta_habilidades():
    _reset_state()
    official = client.post("/api/versions", json={"description": BACKEND_PYTHON_JOB}).json()
    _reset_state()
    focused = client.post(
        "/api/focused/versions", json={"description": BACKEND_PYTHON_JOB}
    ).json()

    official_frontend = next(
        c for c in official["balanced"]["resume"]["skill_categories"] if c["id"] == "skills-frontend"
    )
    focused_frontend = next(
        c for c in focused["balanced"]["resume"]["skill_categories"] if c["id"] == "skills-frontend"
    )
    # O motor oficial nunca remove: mantém todos os itens originais.
    assert len(official_frontend["items"]) == 5
    # O motor focado corta a categoria secundária.
    assert len(focused_frontend["items"]) <= MAX_SECONDARY_ITEMS


def test_nao_inventa_nenhuma_habilidade_fora_do_curriculo_base():
    from app.resume.base_resume import BASE_RESUME

    _reset_state()
    response = client.post("/api/focused/versions", json={"description": BACKEND_PYTHON_JOB})
    payload = response.json()

    base_items = {item for c in BASE_RESUME.skill_categories for item in c.items}
    for variant_key in ("balanced", "ats_focus", "experience_focus"):
        focused_items = {
            item
            for category in payload[variant_key]["resume"]["skill_categories"]
            for item in category["items"]
        }
        assert focused_items <= base_items


def test_curriculo_base_permanece_intacto():
    _reset_state()
    response = client.post("/api/focused/versions", json={"description": BACKEND_PYTHON_JOB})
    payload = response.json()
    assert payload["base_resume_untouched"] is True
