"""5. Geração das 3 versões adaptadas (fluxo completo) · nome do arquivo."""

from __future__ import annotations

import pytest

from app.ai.heuristic_provider import HeuristicProvider
from app.job.confirmations import SkillConfirmation
from app.job.models import JobInput
from app.pdf.filename import build_pdf_filename
from app.pipeline import STRATEGIES, run_analysis_pipeline, run_version_pipeline
from app.resume.adapt import reset_version_counter
from app.resume.base_resume import BASE_RESUME
from app.versions import clear_versions, list_versions
from tests.fixtures import (
    BACKEND_PYTHON_JOB,
    CLOUD_DEVOPS_JOB,
    FRONTEND_REACT_JOB,
    NO_TECH_JOB,
    build_very_long_job,
)

provider = HeuristicProvider()
BASE_SNAPSHOT = BASE_RESUME.model_dump_json()


@pytest.fixture(autouse=True)
def _reset_state():
    reset_version_counter()
    clear_versions()
    yield


async def analyze(description: str, **kwargs):
    return await run_analysis_pipeline(
        JobInput(description=description, **kwargs), provider=provider
    )


async def create_version(description: str, **kwargs):
    return await run_version_pipeline(
        JobInput(description=description, **kwargs), provider=provider
    )


class TestAnalise:
    """A tela principal avalia o currículo BASE — não adapta nada."""

    @pytest.mark.anyio
    async def test_preview_e_o_curriculo_base_puro(self):
        result = await analyze(FRONTEND_REACT_JOB)

        assert result.base_resume.kind == "base"
        assert result.base_resume.summary == BASE_RESUME.summary
        assert result.base_resume.skill_categories == BASE_RESUME.skill_categories
        assert result.base_resume.experience == BASE_RESUME.experience

    @pytest.mark.anyio
    async def test_curriculo_base_sempre_valido(self):
        result = await analyze(BACKEND_PYTHON_JOB)
        assert result.validation.is_valid is True

    @pytest.mark.anyio
    async def test_recomenda_adaptacao_para_vaga_frontend(self):
        result = await analyze(FRONTEND_REACT_JOB)

        assert result.recommendation.detected_archetype == "frontend"
        assert result.recommendation.recommended is True
        assert result.recommendation.reasons

    @pytest.mark.anyio
    async def test_detecta_arquetipos_por_tipo_de_vaga(self):
        assert (await analyze(FRONTEND_REACT_JOB)).recommendation.detected_archetype == "frontend"
        assert (await analyze(CLOUD_DEVOPS_JOB)).recommendation.detected_archetype == "devops"
        backend = (await analyze(BACKEND_PYTHON_JOB)).recommendation.detected_archetype
        assert backend in ("backend", "fullstack")

    @pytest.mark.anyio
    async def test_vaga_sem_tecnologia_nao_recomenda_nada(self):
        result = await analyze(NO_TECH_JOB)
        assert result.recommendation.recommended is False
        assert result.recommendation.detected_archetype is None

    @pytest.mark.anyio
    async def test_expoe_perguntas_de_gap_pendentes(self):
        result = await analyze(BACKEND_PYTHON_JOB)
        terms = {q.term for q in result.pending_gap_questions}
        # Kubernetes e Terraform são diferenciais da vaga sem evidência no base.
        assert "Kubernetes" in terms
        assert "Terraform" in terms
        assert all(q.answer is None for q in result.pending_gap_questions)


class TestCriacaoDeVersao:
    @pytest.mark.anyio
    async def test_gera_exatamente_3_estrategias(self):
        result = await create_version(FRONTEND_REACT_JOB)

        assert result.balanced.strategy == "balanced"
        assert result.ats_focus.strategy == "ats_focus"
        assert result.experience_focus.strategy == "experience_focus"
        assert result.base_resume_untouched is True
        for variant in (result.balanced, result.ats_focus, result.experience_focus):
            assert variant.validation.is_valid is True

    @pytest.mark.anyio
    async def test_estrategias_nao_removem_nem_inventam_nada(self):
        result = await create_version(CLOUD_DEVOPS_JOB)

        for variant in (result.balanced, result.ats_focus, result.experience_focus):
            adapted = variant.adaptation.resume
            assert adapted.basics == BASE_RESUME.basics
            assert adapted.projects == BASE_RESUME.projects
            assert adapted.education == BASE_RESUME.education
            assert adapted.languages == BASE_RESUME.languages
            # Nenhuma habilidade omitida: só a ordem pode mudar (sem confirmações).
            assert sorted(i for c in adapted.skill_categories for i in c.items) == sorted(
                i for c in BASE_RESUME.skill_categories for i in c.items
            )
            assert {b.text for e in adapted.experience for b in e.bullets} == {
                b.text for e in BASE_RESUME.experience for b in e.bullets
            }

    @pytest.mark.anyio
    async def test_oferece_multiplas_redacoes_do_arquetipo(self):
        result = await create_version(FRONTEND_REACT_JOB)

        assert len(result.summary_options) >= 2
        assert all(o.archetype_id == "frontend" for o in result.summary_options)
        assert len({o.text for o in result.summary_options}) == len(result.summary_options)

    @pytest.mark.anyio
    async def test_permite_travar_a_mesma_redacao_nas_3_estrategias(self):
        first = await create_version(FRONTEND_REACT_JOB)
        chosen_option = first.summary_options[1]

        chosen = await run_version_pipeline(
            JobInput(description=FRONTEND_REACT_JOB),
            summary_option_id=chosen_option.id,
            provider=provider,
        )

        for variant in (chosen.balanced, chosen.ats_focus, chosen.experience_focus):
            assert variant.adaptation.resume.summary == chosen_option.text

    @pytest.mark.anyio
    async def test_permite_trocar_o_arquetipo_manualmente(self):
        result = await run_version_pipeline(
            JobInput(description=FRONTEND_REACT_JOB),
            archetype_id="devops",
            provider=provider,
        )
        assert all(o.archetype_id == "devops" for o in result.summary_options)

    @pytest.mark.anyio
    async def test_3_nunca_adiciona_tecnologia_que_o_candidato_nao_tem(self):
        result = await create_version(BACKEND_PYTHON_JOB)

        for variant in (result.balanced, result.ats_focus, result.experience_focus):
            serialized = variant.adaptation.resume.model_dump_json()
            assert "Kubernetes" not in serialized
            assert "Terraform" not in serialized

        gaps = {item.term for item in (*result.match.missing, *result.match.weak)}
        assert "Kubernetes" in gaps

    @pytest.mark.anyio
    async def test_mantem_base_intacto_e_cria_novas_versoes(self):
        first = await create_version(BACKEND_PYTHON_JOB)
        second = await create_version(FRONTEND_REACT_JOB)

        assert first.base_resume_untouched is True
        assert second.base_resume_untouched is True
        assert BASE_RESUME.model_dump_json() == BASE_SNAPSHOT

        # Três variantes por chamada => seis versões registradas.
        assert len(list_versions()) == 6

    @pytest.mark.anyio
    async def test_9_vaga_muito_longa(self):
        result = await create_version(build_very_long_job())
        for variant in (result.balanced, result.ats_focus, result.experience_focus):
            assert variant.validation.is_valid is True

    @pytest.mark.anyio
    async def test_10_vaga_sem_tecnologias_nao_quebra(self):
        result = await create_version(NO_TECH_JOB)

        for variant in (result.balanced, result.ats_focus, result.experience_focus):
            assert variant.validation.is_valid is True
        # Sem arquétipo detectado, a redação cai no resumo do currículo base.
        assert result.summary_options == ()


class TestRecomendacaoDeVersao:
    """Regra 10 — qual das 3 versões o sistema recomenda."""

    @pytest.mark.anyio
    async def test_recomenda_uma_das_3_estrategias_validas(self):
        result = await create_version(FRONTEND_REACT_JOB)
        assert result.best_variant.strategy in STRATEGIES
        assert result.best_variant.reason

    @pytest.mark.anyio
    async def test_recomendacao_e_deterministica_para_a_mesma_vaga(self):
        first = await create_version(BACKEND_PYTHON_JOB)
        second = await create_version(BACKEND_PYTHON_JOB)
        assert first.best_variant.strategy == second.best_variant.strategy


class TestGapConfirmation:
    """Regra 2 — perguntar antes de assumir gap, nunca inventar."""

    @pytest.mark.anyio
    async def test_sim_adiciona_ao_matching_e_a_versao_adaptada(self):
        confirmations = (
            SkillConfirmation(term="Kubernetes", answer="yes", context="Curso e labs pessoais"),
        )
        result = await run_version_pipeline(
            JobInput(description=BACKEND_PYTHON_JOB),
            provider=provider,
            confirmations=confirmations,
        )

        assert "Kubernetes" not in {q.term for q in result.pending_gap_questions}
        assert any(item.term == "Kubernetes" for item in result.match.strong + result.match.medium)

        adapted = result.balanced.adaptation.resume
        confirmed_category = next(
            c for c in adapted.skill_categories if c.id == "skills-confirmed-for-job"
        )
        assert "Kubernetes" in confirmed_category.items
        assert result.balanced.validation.is_valid is True

    @pytest.mark.anyio
    async def test_nao_nunca_adiciona_ao_curriculo(self):
        confirmations = (SkillConfirmation(term="Kubernetes", answer="no"),)
        result = await run_version_pipeline(
            JobInput(description=BACKEND_PYTHON_JOB),
            provider=provider,
            confirmations=confirmations,
        )

        for variant in (result.balanced, result.ats_focus, result.experience_focus):
            assert "Kubernetes" not in variant.adaptation.resume.model_dump_json()
        assert any(
            item.term == "Kubernetes" for item in (*result.match.missing, *result.match.weak)
        )

    @pytest.mark.anyio
    async def test_nao_tenho_certeza_nao_adiciona_e_fica_nao_confirmado(self):
        confirmations = (SkillConfirmation(term="Kubernetes", answer="unsure"),)
        result = await run_analysis_pipeline(
            JobInput(description=BACKEND_PYTHON_JOB), provider=provider, confirmations=confirmations
        )

        for variant_json in (result.base_resume.model_dump_json(),):
            assert "Kubernetes" not in variant_json
        question = next(q for q in result.pending_gap_questions if q.term == "Kubernetes")
        assert question.answer == "unsure"

    @pytest.mark.anyio
    async def test_curriculo_base_nunca_e_alterado_por_confirmacao(self):
        confirmations = (SkillConfirmation(term="Kubernetes", answer="yes"),)
        await run_version_pipeline(
            JobInput(description=BACKEND_PYTHON_JOB), provider=provider, confirmations=confirmations
        )
        assert BASE_RESUME.model_dump_json() == BASE_SNAPSHOT
        assert "Kubernetes" not in BASE_RESUME.model_dump_json()


class TestPdfFilename:
    def test_usa_empresa(self):
        assert build_pdf_filename(company="Microsoft") == "curriculo-caio-microsoft.pdf"

    def test_ignora_cargo_no_nome(self):
        assert (
            build_pdf_filename(company="Microsoft", job_title="Backend Python")
            == "curriculo-caio-microsoft.pdf"
        )

    def test_sem_empresa(self):
        assert build_pdf_filename() == "curriculo-caio.pdf"

    def test_nome_valido_com_acentos_e_simbolos(self):
        assert build_pdf_filename(company="Ítaú Unibanco S/A") == "curriculo-caio-itau-unibanco-s-a.pdf"

    @pytest.mark.anyio
    async def test_funciona_sem_empresa(self):
        result = await create_version(BACKEND_PYTHON_JOB)
        assert result.pdf_filename == "curriculo-caio.pdf"

    @pytest.mark.anyio
    async def test_funciona_com_empresa(self):
        result = await create_version(BACKEND_PYTHON_JOB, company="Nubank")
        assert result.pdf_filename == "curriculo-caio-nubank.pdf"
