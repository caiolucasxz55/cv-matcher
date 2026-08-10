"""Camada HTTP das rotas de habilidades do currículo base."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.fixtures import BACKEND_PYTHON_JOB

client = TestClient(app)


def test_get_lista_categorias_e_termos_disponiveis():
    response = client.get("/api/base-resume/skills")
    assert response.status_code == 200
    payload = response.json()

    ids = {category["id"] for category in payload["categories"]}
    assert "skills-eng" in ids
    assert "Automação" in payload["available_terms"]


def test_adiciona_e_reflete_na_analise():
    added = client.post(
        "/api/base-resume/skills", json={"category_id": "skills-eng", "term": "Automação"}
    )
    assert added.status_code == 200
    eng = next(c for c in added.json()["categories"] if c["id"] == "skills-eng")
    assert {"name": "Automação", "custom": True, "recognized": True} in eng["items"]

    analysis = client.post("/api/analyze", json={"description": BACKEND_PYTHON_JOB}).json()
    resume_eng = next(
        c for c in analysis["base_resume"]["skill_categories"] if c["id"] == "skills-eng"
    )
    assert "Automação" in resume_eng["items"]


def test_remove_termo_customizado():
    client.post("/api/base-resume/skills", json={"category_id": "skills-eng", "term": "N8N"})
    response = client.post(
        "/api/base-resume/skills/remove", json={"category_id": "skills-eng", "term": "N8N"}
    )
    assert response.status_code == 200
    eng = next(c for c in response.json()["categories"] if c["id"] == "skills-eng")
    assert all(item["name"] != "N8N" for item in eng["items"])


def test_nao_permite_remover_termo_original():
    response = client.post(
        "/api/base-resume/skills/remove", json={"category_id": "skills-eng", "term": "Git"}
    )
    assert response.status_code == 409


def test_rejeita_categoria_inexistente():
    response = client.post(
        "/api/base-resume/skills", json={"category_id": "nao-existe", "term": "Python"}
    )
    assert response.status_code == 404


def test_aceita_termo_livre_fora_da_taxonomia_marcado_como_nao_reconhecido():
    response = client.post(
        "/api/base-resume/skills", json={"category_id": "skills-eng", "term": "Coisa Aleatoria"}
    )
    assert response.status_code == 200
    eng = next(c for c in response.json()["categories"] if c["id"] == "skills-eng")
    assert {"name": "Coisa Aleatoria", "custom": True, "recognized": False} in eng["items"]


def test_rejeita_termo_em_branco():
    response = client.post(
        "/api/base-resume/skills", json={"category_id": "skills-eng", "term": "   "}
    )
    assert response.status_code == 422


def test_rejeita_termo_duplicado():
    response = client.post(
        "/api/base-resume/skills", json={"category_id": "skills-eng", "term": "Git"}
    )
    assert response.status_code == 409
