"""Habilidades customizadas: adicao/remocao e integracao com o pipeline."""

from __future__ import annotations

import pytest

from app.resume.base_resume import BASE_RESUME
from app.resume.skills_store import (
    DuplicateTermError,
    InvalidTermError,
    NotCustomTermError,
    UnknownCategoryError,
    add_custom_skill,
    get_base_resume,
    remove_custom_skill,
    reset_cache,
    skills_overview,
)


def test_sem_customizacao_retorna_o_proprio_base_resume():
    assert get_base_resume() is BASE_RESUME


def test_adiciona_termo_do_vocabulario_controlado():
    overview = add_custom_skill(category_id="skills-eng", term="automação")

    eng = next(c for c in overview["categories"] if c["id"] == "skills-eng")
    assert {"name": "Automação", "custom": True, "recognized": True} in eng["items"]
    assert "Automação" not in overview["available_terms"]


def test_adiciona_termo_fora_do_vocabulario_controlado():
    """A lista fechada e so uma sugestao: qualquer texto pode ser adicionado."""
    overview = add_custom_skill(category_id="skills-eng", term="Liderança de squads")

    eng = next(c for c in overview["categories"] if c["id"] == "skills-eng")
    assert {
        "name": "Liderança de squads",
        "custom": True,
        "recognized": False,
    } in eng["items"]


def test_termo_customizado_aparece_no_curriculo_base_dinamico():
    add_custom_skill(category_id="skills-eng", term="N8N")

    resume = get_base_resume()
    eng = next(c for c in resume.skill_categories if c.id == "skills-eng")
    assert "N8N" in eng.items


def test_persiste_entre_resets_de_cache():
    add_custom_skill(category_id="skills-cloud", term="Self-hosting")
    reset_cache()

    resume = get_base_resume()
    cloud = next(c for c in resume.skill_categories if c.id == "skills-cloud")
    assert "Self-hosting" in cloud.items


def test_categoria_inexistente_gera_erro():
    with pytest.raises(UnknownCategoryError):
        add_custom_skill(category_id="skills-inexistente", term="Python")


def test_termo_vazio_gera_erro():
    with pytest.raises(InvalidTermError):
        add_custom_skill(category_id="skills-eng", term="   ")


def test_termo_ja_declarado_gera_erro():
    with pytest.raises(DuplicateTermError):
        add_custom_skill(category_id="skills-eng", term="Git")


def test_termo_customizado_duplicado_gera_erro_ignorando_caixa():
    add_custom_skill(category_id="skills-eng", term="Liderança de squads")
    with pytest.raises(DuplicateTermError):
        add_custom_skill(category_id="skills-eng", term="liderança DE SQUADS")


def test_remove_apenas_termo_customizado():
    add_custom_skill(category_id="skills-eng", term="Automação")
    overview = remove_custom_skill(category_id="skills-eng", term="Automação")

    eng = next(c for c in overview["categories"] if c["id"] == "skills-eng")
    assert all(item["name"] != "Automação" for item in eng["items"])
    assert "Automação" in overview["available_terms"]


def test_nao_remove_termo_original_do_base_resume():
    with pytest.raises(NotCustomTermError):
        remove_custom_skill(category_id="skills-eng", term="Git")


def test_overview_marca_itens_originais_como_nao_customizados():
    overview = skills_overview()
    eng = next(c for c in overview["categories"] if c["id"] == "skills-eng")
    assert all(item["custom"] is False for item in eng["items"])
    assert all(item["recognized"] is True for item in eng["items"])
