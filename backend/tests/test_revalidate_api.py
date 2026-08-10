"""POST /api/revalidate — botão "Reanalisar" (regra 12).

Recalcula match + validação + recomendação juntos a partir do currículo
editado — nunca só a validação isolada.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.resume.adapt import reset_version_counter
from app.versions import clear_versions
from tests.fixtures import BACKEND_PYTHON_JOB

client = TestClient(app)


def _create_version():
    reset_version_counter()
    clear_versions()
    return client.post("/api/versions", json={"description": BACKEND_PYTHON_JOB}).json()


def test_revalida_curriculo_inalterado_como_valido():
    created = _create_version()
    response = client.post(
        "/api/revalidate",
        json={"resume": created["balanced"]["resume"], "analysis": created["analysis"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"]["is_valid"] is True
    assert payload["match"]["job_match_score"] == created["match"]["job_match_score"]


def test_detecta_habilidade_inventada_apos_edicao():
    created = _create_version()
    resume = created["balanced"]["resume"]
    resume["skill_categories"][0]["items"].append("Kubernetes")

    response = client.post(
        "/api/revalidate",
        json={"resume": resume, "analysis": created["analysis"]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"]["is_valid"] is False
    assert "Kubernetes" in {item["value"] for item in payload["validation"]["hallucinations"]}


def test_aceita_habilidade_evidenciada_mas_ainda_nao_declarada():
    created = _create_version()
    resume = created["balanced"]["resume"]
    # "Eye Tracking" tem evidência num bullet de experiência, mas não é uma
    # habilidade declarada — adicioná-la deve permanecer válido.
    resume["skill_categories"][0]["items"].append("Eye Tracking")

    response = client.post(
        "/api/revalidate",
        json={"resume": resume, "analysis": created["analysis"]},
    )
    assert response.status_code == 200
    assert response.json()["validation"]["is_valid"] is True


def test_remover_habilidade_permanece_valido():
    created = _create_version()
    resume = created["balanced"]["resume"]
    resume["skill_categories"][0]["items"].pop()

    response = client.post(
        "/api/revalidate",
        json={"resume": resume, "analysis": created["analysis"]},
    )
    assert response.status_code == 200
    assert response.json()["validation"]["is_valid"] is True


def test_reanalisar_recalcula_match_nao_so_validacao():
    """Regra 12 — o bug original: adicionar uma habilidade evidenciada só na
    skills (ex.: Eye Tracking, que só tinha evidência em bullet) devia
    reduzir os gaps mostrados no MatchReport, não só passar na validação."""
    created = _create_version()
    resume = created["balanced"]["resume"]

    before = client.post(
        "/api/revalidate", json={"resume": resume, "analysis": created["analysis"]}
    ).json()

    # Confirma Kubernetes (regra 2) e reanalisa: o gap deve sumir do match.
    response = client.post(
        "/api/revalidate",
        json={
            "resume": resume,
            "analysis": created["analysis"],
            "confirmations": [{"term": "Kubernetes", "answer": "yes"}],
        },
    )
    after = response.json()

    def gap_terms(payload):
        return {item["term"] for item in (*payload["match"]["missing"], *payload["match"]["weak"])}

    assert "Kubernetes" in gap_terms(before)
    assert "Kubernetes" not in gap_terms(after)
    # A recomendação também precisa vir junto na resposta.
    assert "recommendation" in after
    assert "pending_gap_questions" in after
