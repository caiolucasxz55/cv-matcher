"""1. Análise da vaga · 2. Matching de tecnologias."""

from __future__ import annotations

from app.job.analyze import analyze_job_deterministic, merge_ai_signals
from app.job.models import JobInput
from app.job.taxonomy import detect_terms
from tests.fixtures import (
    BACKEND_PYTHON_JOB,
    CLOUD_DEVOPS_JOB,
    FRONTEND_REACT_JOB,
    NO_TECH_JOB,
    build_very_long_job,
)


def analyze(description: str, **kwargs) -> object:
    return analyze_job_deterministic(JobInput(description=description, **kwargs))


class TestJobAnalysis:
    def test_extrai_tecnologias_frameworks_bancos_e_cloud(self):
        analysis = analyze(BACKEND_PYTHON_JOB)

        assert "Python" in analysis.programming_languages
        assert "FastAPI" in analysis.frameworks
        assert "PostgreSQL" in analysis.databases
        assert "Docker" in analysis.devops
        assert "AWS" in analysis.cloud
        assert "REST APIs" in analysis.keywords

    def test_distingue_obrigatorio_de_desejavel(self):
        analysis = analyze(BACKEND_PYTHON_JOB)

        assert "Python" in analysis.required_skills
        assert "FastAPI" in analysis.required_skills
        assert "Docker" in analysis.required_skills

        assert "Kubernetes" in analysis.preferred_skills
        assert "Terraform" in analysis.preferred_skills

        # Um termo nunca aparece nas duas listas.
        assert not set(analysis.required_skills) & set(analysis.preferred_skills)

    def test_detecta_senioridade_e_responsabilidades(self):
        analysis = analyze(BACKEND_PYTHON_JOB)
        assert analysis.seniority == "pleno"
        assert len(analysis.responsibilities) > 0

    def test_nao_gera_requisitos_da_secao_de_beneficios(self):
        analysis = analyze(BACKEND_PYTHON_JOB)
        evidences = " ".join(r.evidence for r in analysis.requirements)
        assert "plano de saúde" not in evidences

    def test_keywords_ats_sem_duplicatas(self):
        analysis = analyze(CLOUD_DEVOPS_JOB)
        assert len(set(analysis.ats_keywords)) == len(analysis.ats_keywords)

    def test_9_vaga_muito_longa(self):
        description = build_very_long_job()
        assert len(description) > 30_000
        analysis = analyze(description)
        assert "Python" in analysis.required_skills

    def test_10_vaga_sem_tecnologias(self):
        analysis = analyze(NO_TECH_JOB)
        assert analysis.technologies == ()
        assert analysis.seniority == "junior"

    def test_merge_ai_descarta_termos_fora_da_taxonomia(self):
        base = analyze(FRONTEND_REACT_JOB)
        merged = merge_ai_signals(
            base,
            required_terms=["React", "Tecnologia Inventada XYZ", "Vue"],
            preferred_terms=["Outra Coisa Falsa"],
        )

        assert "React" in merged.required_skills
        assert "Vue" in merged.required_skills
        assert "Tecnologia Inventada XYZ" not in merged.required_skills
        assert "Outra Coisa Falsa" not in merged.preferred_skills


class TestTaxonomy:
    def test_normaliza_sinonimos_para_canonico(self):
        canonical = {
            item.canonical
            for item in detect_terms(
                "Trabalhamos com nodejs, postgres, k8s e integração contínua."
            )
        }
        assert {"Node.js", "PostgreSQL", "Kubernetes", "CI/CD"} <= canonical

    def test_respeita_fronteiras_em_termos_com_pontuacao(self):
        canonical = {
            item.canonical for item in detect_terms("Stack: C#, .NET, CI/CD e Node.js.")
        }
        assert {"C#", ".NET", "CI/CD", "Node.js"} <= canonical

    def test_nao_confunde_substrings_com_termos_reais(self):
        canonical = {
            item.canonical
            for item in detect_terms("Somos uma javaria e trabalhamos com javascript.")
        }
        assert "JavaScript" in canonical
        assert "Java" not in canonical
