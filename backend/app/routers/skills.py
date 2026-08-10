"""Rotas de gerenciamento das habilidades declaradas no curriculo base.

Diferente de `/analyze` e `/versions`, estas rotas ALTERAM o curriculo base —
mas apenas a lista de habilidades. Aceitam qualquer texto (nao so o
vocabulario controlado); `recognized` informa se o termo entra no matching
automatico com vagas. Quem decide o que entra e sempre a pessoa, nunca a IA.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.resume.skills_store import (
    DuplicateTermError,
    InvalidTermError,
    NotCustomTermError,
    UnknownCategoryError,
    add_custom_skill,
    remove_custom_skill,
    skills_overview,
)

router = APIRouter(prefix="/base-resume/skills", tags=["skills"])


class SkillItemOut(BaseModel):
    name: str
    custom: bool
    recognized: bool


class SkillCategoryOut(BaseModel):
    id: str
    label: str
    items: list[SkillItemOut]


class SkillsOverviewOut(BaseModel):
    categories: list[SkillCategoryOut]
    available_terms: tuple[str, ...]


class SkillMutationPayload(BaseModel):
    category_id: str = Field(min_length=1, max_length=40)
    term: str = Field(min_length=1, max_length=80)


@router.get("", response_model=SkillsOverviewOut)
async def get_skills() -> SkillsOverviewOut:
    return SkillsOverviewOut(**skills_overview())


@router.post("", response_model=SkillsOverviewOut)
async def add_skill(payload: SkillMutationPayload) -> SkillsOverviewOut:
    try:
        return SkillsOverviewOut(
            **add_custom_skill(category_id=payload.category_id, term=payload.term)
        )
    except UnknownCategoryError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoria inexistente."
        ) from None
    except InvalidTermError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Digite um nome de habilidade válido.",
        ) from None
    except DuplicateTermError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Essa habilidade já está no currículo.",
        ) from None


@router.post("/remove", response_model=SkillsOverviewOut)
async def remove_skill(payload: SkillMutationPayload) -> SkillsOverviewOut:
    try:
        return SkillsOverviewOut(
            **remove_custom_skill(category_id=payload.category_id, term=payload.term)
        )
    except NotCustomTermError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Só é possível remover habilidades adicionadas por você.",
        ) from None
