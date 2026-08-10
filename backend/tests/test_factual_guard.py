"""4. Validação factual (anti-alucinação)."""

from __future__ import annotations

import pytest

from app.resume.base_resume import BASE_RESUME
from app.resume.evidence import build_evidence_index
from app.validation.auto_fix import auto_fix
from app.validation.factual_guard import run_factual_guard


@pytest.fixture(scope="module")
def index():
    return build_evidence_index(BASE_RESUME)


def _with_extra_skill(term: str):
    categories = tuple(
        category.model_copy(update={"items": (*category.items, term)})
        if category.id == "skills-cloud"
        else category
        for category in BASE_RESUME.skill_categories
    )
    return BASE_RESUME.model_copy(update={"skill_categories": categories})


def test_aprova_o_proprio_curriculo_base(index):
    result = run_factual_guard(BASE_RESUME, index)
    assert result.hallucinations == ()
    assert result.unsupported_claims == ()
    assert result.ok is True


def test_detecta_tecnologia_inventada_nas_habilidades(index):
    result = run_factual_guard(_with_extra_skill("Kubernetes"), index)
    assert result.ok is False
    assert "Kubernetes" in {finding.value for finding in result.hallucinations}


def test_detecta_metrica_inventada_em_bullet(index):
    experience = BASE_RESUME.experience[0]
    bullets = list(experience.bullets)
    bullets[0] = bullets[0].model_copy(
        update={"text": f"{bullets[0].text} Reduzi custos em 87%."}
    )
    tampered = BASE_RESUME.model_copy(
        update={
            "experience": (experience.model_copy(update={"bullets": tuple(bullets)}),)
        }
    )

    result = run_factual_guard(tampered, index)
    assert result.ok is False
    assert any("87" in finding.value for finding in result.unsupported_claims)


def test_detecta_empresa_inventada(index):
    tampered = BASE_RESUME.model_copy(
        update={
            "experience": tuple(
                exp.model_copy(update={"company": "Globex Corporation"})
                for exp in BASE_RESUME.experience
            )
        }
    )
    assert run_factual_guard(tampered, index).ok is False


def test_auto_fix_remove_tecnologia_inventada(index):
    fixed = auto_fix(_with_extra_skill("Kubernetes"), BASE_RESUME, index)

    assert fixed.applied
    all_items = [item for c in fixed.resume.skill_categories for item in c.items]
    assert "Kubernetes" not in all_items
    assert run_factual_guard(fixed.resume, index).ok is True


def test_auto_fix_restaura_bullet_adulterado(index):
    experience = BASE_RESUME.experience[0]
    original = experience.bullets[0]
    bullets = list(experience.bullets)
    bullets[0] = original.model_copy(
        update={"text": "Liderei uma equipe de 12 engenheiros na Globex."}
    )
    tampered = BASE_RESUME.model_copy(
        update={
            "experience": (experience.model_copy(update={"bullets": tuple(bullets)}),)
        }
    )

    fixed = auto_fix(tampered, BASE_RESUME, index)
    restored = next(
        bullet
        for bullet in fixed.resume.experience[0].bullets
        if bullet.id == original.id
    )
    assert restored.text == original.text
