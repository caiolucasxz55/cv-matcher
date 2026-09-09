"""Rota do "Currículo versão Gupy": gera os dois blocos de texto que a Gupy
(e ATS parecidos, que não aceitam PDF direto) exigem em campos separados —
parágrafo de atividades e lista de palavras-chave — com ênfase no que mais
importa para a vaga colada. Roda o mesmo pipeline de ANÁLISE do fluxo
principal (`run_analysis_pipeline`): nada é adaptado, só reordenado
(`app.resume.gupy_format`)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.pipeline import run_analysis_pipeline
from app.resume.gupy_format import build_activity_paragraph, build_keyword_list
from app.routers.adapt import JobPayload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gupy", tags=["gupy"])


class GupyResponse(BaseModel):
    #: Parágrafo pronto para o campo "Descrição de atividades" da Gupy.
    activity_description: str
    #: Habilidades declaradas, ordenadas por relevância para a vaga.
    keywords: tuple[str, ...]
    match_score: int
    #: Cargo/empresa da experiência usada no parágrafo (hoje só existe uma).
    role: str
    company: str


@router.post("", response_model=GupyResponse)
async def build_gupy_format(payload: JobPayload) -> GupyResponse:
    try:
        result = await run_analysis_pipeline(
            payload.to_job_input(), confirmations=payload.to_confirmations()
        )
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao gerar o currículo no formato Gupy")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível gerar o currículo no formato Gupy. Tente novamente.",
        ) from None

    experience = result.base_resume.experience[0] if result.base_resume.experience else None
    activity_description = (
        build_activity_paragraph(experience, result.match.relevance) if experience else ""
    )
    keywords = build_keyword_list(result.base_resume.skill_categories, result.match.relevance)

    return GupyResponse(
        activity_description=activity_description,
        keywords=tuple(keywords),
        match_score=result.match.job_match_score,
        role=experience.role if experience else "",
        company=experience.company if experience else "",
    )
