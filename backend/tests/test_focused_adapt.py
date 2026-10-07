"""CV Matcher Novo — a seção de habilidades deve ser CURADA pela categoria
dominante da vaga (ao contrário do motor oficial, que só reordena e nunca
remove nada declarado)."""

from __future__ import annotations

import pytest

from app.ai.heuristic_provider import HeuristicProvider
from app.job.analyze import analyze_job_deterministic
from app.job.matching import build_match_report
from app.job.models import JobInput
from app.resume.adapt import reset_version_counter
from app.resume.base_resume import BASE_RESUME
from app.resume.evidence import build_evidence_index
from app.resume.focused_adapt import (
    MAX_SECONDARY_ITEMS,
    adapt_resume_focused,
    detect_dominant_category_ids,
    focus_skills,
)
from tests.fixtures import BACKEND_PYTHON_JOB, FRONTEND_REACT_JOB, NO_TECH_JOB

provider = HeuristicProvider()
INDEX = build_evidence_index(BASE_RESUME)


@pytest.fixture(autouse=True)
def _reset_state():
    reset_version_counter()
    yield


def _analysis_and_match(description: str):
    analysis = analyze_job_deterministic(JobInput(description=description))
    match = build_match_report(analysis, INDEX)
    return analysis, match


class TestDetectDominantCategory:
    def test_vaga_backend_detecta_categoria_backend(self):
        analysis, match = _analysis_and_match(BACKEND_PYTHON_JOB)
        assert detect_dominant_category_ids(analysis, match, INDEX) == ("skills-backend",)

    def test_vaga_frontend_detecta_categoria_frontend(self):
        analysis, match = _analysis_and_match(FRONTEND_REACT_JOB)
        assert detect_dominant_category_ids(analysis, match, INDEX) == ("skills-frontend",)

    def test_vaga_sem_tecnologia_nao_tem_categoria_dominante(self):
        analysis, match = _analysis_and_match(NO_TECH_JOB)
        assert detect_dominant_category_ids(analysis, match, INDEX) == ()


class TestFocusSkills:
    def test_sem_dominante_mantem_todos_os_itens_so_reordena(self):
        categories, changes = focus_skills(BASE_RESUME.skill_categories, {}, ())
        original_items = {item for c in BASE_RESUME.skill_categories for item in c.items}
        focused_items = {item for c in categories for item in c.items}
        assert focused_items == original_items
        assert changes == []

    def test_categoria_dominante_fica_inteira_e_primeiro(self):
        categories, changes = focus_skills(
            BASE_RESUME.skill_categories, {"Python": 1.0}, ("skills-backend",)
        )
        backend = next(c for c in BASE_RESUME.skill_categories if c.id == "skills-backend")
        assert categories[0].id == "skills-backend"
        assert set(categories[0].items) == set(backend.items)
        assert any("mantida" in change for change in changes)

    def test_categorias_secundarias_sao_cortadas(self):
        categories, changes = focus_skills(
            BASE_RESUME.skill_categories, {"Python": 1.0}, ("skills-backend",)
        )
        for category in categories:
            if category.id == "skills-backend":
                continue
            assert len(category.items) <= MAX_SECONDARY_ITEMS
        assert any("reduzida" in change for change in changes)

    def test_nenhum_item_e_inventado(self):
        categories, _ = focus_skills(
            BASE_RESUME.skill_categories, {"Python": 1.0}, ("skills-backend",)
        )
        original_items = {item for c in BASE_RESUME.skill_categories for item in c.items}
        focused_items = {item for c in categories for item in c.items}
        assert focused_items <= original_items


class TestAdaptResumeFocused:
    @pytest.mark.anyio
    async def test_vaga_backend_resulta_em_curriculo_focado_em_backend(self):
        analysis, match = _analysis_and_match(BACKEND_PYTHON_JOB)
        adaptation = adapt_resume_focused(
            base=BASE_RESUME, index=INDEX, analysis=analysis, match=match
        )
        resume = adaptation.resume

        assert resume.skill_categories[0].id == "skills-backend"
        frontend = next(c for c in resume.skill_categories if c.id == "skills-frontend")
        assert len(frontend.items) <= MAX_SECONDARY_ITEMS

        # Nada novo foi inventado: toda habilidade listada já existia no base.
        base_items = {item for c in BASE_RESUME.skill_categories for item in c.items}
        focused_items = {item for c in resume.skill_categories for item in c.items}
        assert focused_items <= base_items

    @pytest.mark.anyio
    async def test_curriculo_base_nunca_e_alterado(self):
        snapshot = BASE_RESUME.model_dump_json()
        analysis, match = _analysis_and_match(BACKEND_PYTHON_JOB)
        adapt_resume_focused(base=BASE_RESUME, index=INDEX, analysis=analysis, match=match)
        assert BASE_RESUME.model_dump_json() == snapshot
