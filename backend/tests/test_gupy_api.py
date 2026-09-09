"""Testes HTTP do endpoint POST /api/gupy — currículo versão Gupy."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.resume.base_resume import BASE_RESUME
from tests.fixtures import BACKEND_PYTHON_JOB, FRONTEND_REACT_JOB

client = TestClient(app)


def test_gera_paragrafo_e_keywords_com_enfase_na_vaga():
    response = client.post("/api/gupy", json={"description": BACKEND_PYTHON_JOB})
    assert response.status_code == 200
    payload = response.json()

    assert payload["match_score"] > 0
    assert "Python" in payload["keywords"]
    assert payload["role"] == "Desenvolvedor Full Stack Júnior"
    assert payload["company"] == "Inoltra-Tech"

    backend_bullet = next(
        b.text for b in BASE_RESUME.experience[0].bullets if b.id == "exp-inoltra-b2"
    )
    eye_tracking_bullet = next(
        b.text for b in BASE_RESUME.experience[0].bullets if b.id == "exp-inoltra-b4"
    )
    description = payload["activity_description"]
    assert description.index(backend_bullet) < description.index(eye_tracking_bullet)


def test_paragrafo_nunca_inventa_texto_fora_do_curriculo_base():
    response = client.post("/api/gupy", json={"description": FRONTEND_REACT_JOB})
    payload = response.json()

    bullet_texts = [b.text for b in BASE_RESUME.experience[0].bullets]
    for text in bullet_texts:
        assert text in payload["activity_description"]


def test_keywords_refletem_so_habilidades_declaradas_com_evidencia():
    response = client.post("/api/gupy", json={"description": FRONTEND_REACT_JOB})
    payload = response.json()

    all_declared = {item for category in BASE_RESUME.skill_categories for item in category.items}
    assert set(payload["keywords"]) <= all_declared


def test_valida_descricao_minima_como_analyze():
    response = client.post("/api/gupy", json={"description": "curta demais"})
    assert response.status_code == 422
