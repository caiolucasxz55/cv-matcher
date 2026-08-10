"""2/3. Sistema de match e proteção contra tecnologias inexistentes."""

from __future__ import annotations

import pytest

from app.job.analyze import analyze_job_deterministic
from app.job.matching import build_match_report, classify_term
from app.job.models import JobInput
from app.resume.base_resume import BASE_RESUME
from app.resume.evidence import build_evidence_index
from tests.fixtures import BACKEND_PYTHON_JOB


@pytest.fixture(scope="module")
def index():
    return build_evidence_index(BASE_RESUME)


def test_niveis_de_match_do_exemplo_da_especificacao(index):
    assert classify_term(index, "Python").level == "STRONG"
    assert classify_term(index, "FastAPI").level == "STRONG"
    assert classify_term(index, "Azure").level == "STRONG"
    assert classify_term(index, "PostgreSQL").level == "MEDIUM"
    assert classify_term(index, "Kubernetes").level != "STRONG"


def test_kubernetes_nunca_e_match_forte_ou_medio(index):
    kubernetes = classify_term(index, "Kubernetes")
    assert kubernetes.level in ("WEAK", "NONE")
    assert kubernetes.evidence == ()


def test_conceito_relacionado_vira_match_fraco_com_origem(index):
    gcp = classify_term(index, "GCP")
    assert gcp.level == "WEAK"
    assert gcp.related_via is not None
    assert gcp.evidence == ()


def test_tecnologia_inexistente_nao_tem_evidencia(index):
    terraform = classify_term(index, "Terraform")
    assert terraform.evidence == ()
    assert terraform.level not in ("STRONG", "MEDIUM")


def test_score_de_match_e_lista_de_gaps(index):
    analysis = analyze_job_deterministic(JobInput(description=BACKEND_PYTHON_JOB))
    report = build_match_report(analysis, index)

    assert 0 < report.job_match_score <= 100
    strong_terms = {item.term for item in report.strong}
    assert {"Python", "FastAPI"} <= strong_terms

    non_strong = {item.term for item in (*report.weak, *report.missing)}
    assert "Kubernetes" in non_strong
    assert "Terraform" in non_strong


def test_relevancia_apenas_para_termos_com_evidencia(index):
    analysis = analyze_job_deterministic(JobInput(description=BACKEND_PYTHON_JOB))
    report = build_match_report(analysis, index)

    assert report.relevance.get("Python", 0) > 0
    assert "Kubernetes" not in report.relevance
    assert "Terraform" not in report.relevance
