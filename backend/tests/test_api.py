"""Testes da camada HTTP (FastAPI)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.resume.adapt import reset_version_counter
from app.versions import clear_versions
from tests.fixtures import BACKEND_PYTHON_JOB, FRONTEND_REACT_JOB

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_state():
    reset_version_counter()
    clear_versions()
    yield


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


class TestAnalyze:
    def test_retorna_diagnostico_do_curriculo_base(self):
        response = client.post(
            "/api/analyze",
            json={
                "description": BACKEND_PYTHON_JOB,
                "company": "Nubank",
                "job_title": "Backend Python",
            },
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["base_resume"]["kind"] == "base"
        assert payload["validation"]["is_valid"] is True
        assert payload["match"]["job_match_score"] > 0
        assert payload["pdf_filename"] == "curriculo-caio-nubank.pdf"

    def test_nao_adapta_nada(self):
        payload = client.post("/api/analyze", json={"description": FRONTEND_REACT_JOB}).json()
        # O resumo exibido é o do currículo base, sem ênfase aplicada.
        assert payload["base_resume"]["summary"].startswith(
            "Desenvolvedor Full Stack com experiência no desenvolvimento e evolução"
        )

    def test_traz_recomendacao_e_ranking_de_arquetipos(self):
        payload = client.post("/api/analyze", json={"description": FRONTEND_REACT_JOB}).json()
        recommendation = payload["recommendation"]

        assert recommendation["detected_archetype"] == "frontend"
        assert recommendation["recommended"] is True
        assert len(recommendation["ranking"]) == 5

    def test_traz_perguntas_de_gap_pendentes(self):
        payload = client.post("/api/analyze", json={"description": BACKEND_PYTHON_JOB}).json()
        terms = {q["term"] for q in payload["pending_gap_questions"]}
        assert "Kubernetes" in terms

    def test_aceita_confirmacoes_e_reduz_gaps(self):
        payload = client.post(
            "/api/analyze",
            json={
                "description": BACKEND_PYTHON_JOB,
                "confirmations": [{"term": "Kubernetes", "answer": "yes", "context": "Labs pessoais"}],
            },
        ).json()
        terms = {q["term"] for q in payload["pending_gap_questions"]}
        assert "Kubernetes" not in terms

    def test_rejeita_descricao_curta(self):
        assert client.post("/api/analyze", json={"description": "curta"}).status_code == 422

    def test_rejeita_descricao_longa_demais(self):
        response = client.post("/api/analyze", json={"description": "a" * 40_001})
        assert response.status_code == 422


class TestCreateVersion:
    def test_retorna_as_3_estrategias_e_as_redacoes(self):
        response = client.post("/api/versions", json={"description": FRONTEND_REACT_JOB})
        assert response.status_code == 200
        payload = response.json()

        assert payload["balanced"]["strategy"] == "balanced"
        assert payload["ats_focus"]["strategy"] == "ats_focus"
        assert payload["experience_focus"]["strategy"] == "experience_focus"
        assert payload["base_resume_untouched"] is True
        assert len(payload["summary_options"]) >= 2
        assert payload["best_variant"]["strategy"] in (
            "balanced",
            "ats_focus",
            "experience_focus",
        )

    def test_nada_e_removido_entre_as_3_versoes(self):
        payload = client.post("/api/versions", json={"description": FRONTEND_REACT_JOB}).json()
        balanced = payload["balanced"]["resume"]
        ats_focus = payload["ats_focus"]["resume"]

        assert sorted(
            item for cat in balanced["skill_categories"] for item in cat["items"]
        ) == sorted(item for cat in ats_focus["skill_categories"] for item in cat["items"])
        for section in ("projects", "education", "languages", "basics"):
            assert balanced[section] == ats_focus[section]

    def test_permite_escolher_outra_redacao_e_travar_nas_3(self):
        first = client.post("/api/versions", json={"description": FRONTEND_REACT_JOB}).json()
        other = first["summary_options"][1]

        second = client.post(
            "/api/versions",
            json={"description": FRONTEND_REACT_JOB, "summary_option_id": other["id"]},
        ).json()

        for key in ("balanced", "ats_focus", "experience_focus"):
            assert second[key]["resume"]["summary"] == other["text"]

    def test_todas_as_3_variantes_sao_validas(self):
        payload = client.post("/api/versions", json={"description": BACKEND_PYTHON_JOB}).json()
        for key in ("balanced", "ats_focus", "experience_focus"):
            assert payload[key]["validation"]["is_valid"] is True

    def test_confirmacao_sim_aparece_na_versao_adaptada(self):
        payload = client.post(
            "/api/versions",
            json={
                "description": BACKEND_PYTHON_JOB,
                "confirmations": [{"term": "Kubernetes", "answer": "yes"}],
            },
        ).json()
        categories = payload["balanced"]["resume"]["skill_categories"]
        confirmed = next(c for c in categories if c["id"] == "skills-confirmed-for-job")
        assert "Kubernetes" in confirmed["items"]


class TestPdf:
    def test_gera_pdf_da_variante_balanceada(self):
        created = client.post(
            "/api/versions", json={"description": BACKEND_PYTHON_JOB, "company": "Nubank"}
        ).json()

        response = client.post(
            "/api/pdf",
            json={"resume": created["balanced"]["resume"], "company": "Nubank"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "curriculo-caio-nubank.pdf" in response.headers["content-disposition"]
        assert response.content[:5] == b"%PDF-"

    def test_gera_pdf_mesmo_com_tecnologia_inventada(self):
        """A checagem factual audita e loga, mas não bloqueia mais a geração —
        quem decide se segue em frente é a pessoa, não o sistema."""
        created = client.post("/api/versions", json={"description": BACKEND_PYTHON_JOB}).json()
        resume = created["balanced"]["resume"]
        resume["skill_categories"][0]["items"].append("Kubernetes")

        response = client.post("/api/pdf", json={"resume": resume})

        assert response.status_code == 200
        assert response.content[:5] == b"%PDF-"


def test_versions_registra_historico():
    client.post("/api/versions", json={"description": BACKEND_PYTHON_JOB})
    response = client.get("/api/versions")

    assert response.status_code == 200
    history = response.json()
    # Três variantes por criação.
    assert len(history) == 3
    assert {item["strategy"] for item in history} == {"balanced", "ats_focus", "experience_focus"}
