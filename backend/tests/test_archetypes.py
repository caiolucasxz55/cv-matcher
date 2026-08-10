"""Arquétipos: detecção, redações e a regra de evidência."""

from __future__ import annotations

import pytest

from app.job.analyze import analyze_job_deterministic
from app.job.matching import build_match_report
from app.job.models import JobInput
from app.job.taxonomy import detect_terms
from app.resume.archetypes import ARCHETYPES
from app.resume.base_resume import BASE_RESUME
from app.resume.evidence import build_evidence_index
from app.resume.summary_builder import (
    build_summary_options,
    recommend_adaptation,
    score_archetypes,
)
from app.validation.factual_guard import run_factual_guard
from tests.fixtures import BACKEND_PYTHON_JOB, CLOUD_DEVOPS_JOB, FRONTEND_REACT_JOB


@pytest.fixture(scope="module")
def index():
    return build_evidence_index(BASE_RESUME)


def context(description: str, index):
    analysis = analyze_job_deterministic(JobInput(description=description))
    return analysis, build_match_report(analysis, index)


class TestRedacoes:
    def test_toda_redacao_passa_no_guard_factual(self, index):
        """Nenhuma redação pode conter tecnologia ou termo sem evidência."""
        analysis, match = context(FRONTEND_REACT_JOB, index)

        for archetype in ARCHETYPES:
            for option in build_summary_options(archetype.id, index, match.relevance):
                candidate = BASE_RESUME.model_copy(update={"summary": option.text})
                guard = run_factual_guard(candidate, index)
                assert guard.ok, (
                    f"{option.id} reprovou: "
                    f"{[f.value for f in (*guard.hallucinations, *guard.unsupported_claims)]}"
                )

    def test_toda_tecnologia_citada_tem_evidencia(self, index):
        analysis, match = context(BACKEND_PYTHON_JOB, index)

        for archetype in ARCHETYPES:
            for option in build_summary_options(archetype.id, index, match.relevance):
                for tech in option.techs:
                    assert index.has_any_evidence(tech)
                for detected in detect_terms(option.text):
                    assert index.has_any_evidence(detected.canonical), (
                        f"{option.id} cita {detected.canonical} sem evidência"
                    )

    def test_cada_arquetipo_oferece_ao_menos_duas_redacoes(self, index):
        analysis, match = context(FRONTEND_REACT_JOB, index)

        for archetype in ARCHETYPES:
            options = build_summary_options(archetype.id, index, match.relevance)
            assert len(options) >= 2, f"{archetype.id} tem só {len(options)} redação(ões)"

    def test_arquetipo_inexistente_devolve_vazio(self, index):
        assert build_summary_options("nao-existe", index, {}) == []


class TestDeteccao:
    def test_vaga_frontend_ativa_arquetipo_frontend(self, index):
        analysis, match = context(FRONTEND_REACT_JOB, index)
        assert score_archetypes(analysis, match, index)[0].archetype_id == "frontend"

    def test_vaga_devops_ativa_arquetipo_devops(self, index):
        analysis, match = context(CLOUD_DEVOPS_JOB, index)
        assert score_archetypes(analysis, match, index)[0].archetype_id == "devops"

    def test_keyword_sem_evidencia_nao_pontua_arquetipo(self, index):
        """Uma vaga só de Kubernetes/Terraform não deve virar perfil DevOps forte."""
        somente_gaps = (
            "Engenheiro de Plataforma\n\nRequisitos obrigatórios\n"
            "- Kubernetes.\n- Terraform.\n"
        )
        analysis, match = context(somente_gaps, index)
        devops = next(
            item
            for item in score_archetypes(analysis, match, index)
            if item.archetype_id == "devops"
        )
        assert "Kubernetes" in devops.matched_signals
        assert devops.score == 0  # sinal reconhecido, mas sem evidência: não pontua


class TestRecomendacao:
    def test_aponta_keyword_enterrada(self, index):
        """Next.js está nas habilidades mas não no resumo base."""
        analysis, match = context(FRONTEND_REACT_JOB, index)
        recommendation = recommend_adaptation(
            base=BASE_RESUME, analysis=analysis, match=match, index=index
        )

        assert recommendation.recommended is True
        assert recommendation.detected_archetype == "frontend"
        assert any("React" in reason or "TypeScript" in reason for reason in recommendation.reasons)

    def test_ranking_cobre_todos_os_arquetipos(self, index):
        analysis, match = context(BACKEND_PYTHON_JOB, index)
        recommendation = recommend_adaptation(
            base=BASE_RESUME, analysis=analysis, match=match, index=index
        )
        assert len(recommendation.ranking) == len(ARCHETYPES)
        scores = [item.score for item in recommendation.ranking]
        assert scores == sorted(scores, reverse=True)
