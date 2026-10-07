"""Rota do fluxo experimental "CV Matcher Novo" (ver
`app.resume.focused_adapt` e `app.focused_pipeline`). Reaproveita os MESMOS
schemas de entrada/saída de `/api/versions` (`app.routers.adapt`) — a forma
da resposta é idêntica, só o motor de adaptação muda."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.focused_pipeline import run_focused_version_pipeline
from app.routers.adapt import (
    BestVariantOut,
    CreateVersionPayload,
    CreateVersionResponse,
    GapQuestionOut,
    MatchSummary,
    RecommendationOut,
    SummaryOptionOut,
    _to_variant,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/focused", tags=["cv-matcher-novo"])


@router.post("/versions", response_model=CreateVersionResponse)
async def create_focused_version(payload: CreateVersionPayload) -> CreateVersionResponse:
    """"CV Matcher Novo": as mesmas 3 variantes de /api/versions, mas com a
    seção de habilidades curada pela categoria dominante da vaga em vez de
    só reordenada (ver `app.resume.focused_adapt`)."""
    try:
        result = await run_focused_version_pipeline(
            payload.to_job_input(),
            archetype_id=payload.archetype_id,
            summary_option_id=payload.summary_option_id,
            confirmations=payload.to_confirmations(),
        )
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao criar a versão focada (CV Matcher Novo)")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível criar a versão adaptada. Tente novamente.",
        ) from None

    return CreateVersionResponse(
        analysis=result.analysis,
        match=MatchSummary.of(result),
        balanced=_to_variant(result.balanced),
        ats_focus=_to_variant(result.ats_focus),
        experience_focus=_to_variant(result.experience_focus),
        summary_options=tuple(
            SummaryOptionOut(**option.__dict__) for option in result.summary_options
        ),
        recommendation=RecommendationOut.of(result.recommendation),
        best_variant=BestVariantOut(
            strategy=result.best_variant.strategy,
            label=result.best_variant.label,
            reason=result.best_variant.reason,
        ),
        pdf_filename=result.pdf_filename,
        provider_name=result.provider_name,
        base_resume_untouched=result.base_resume_untouched,
        pending_gap_questions=tuple(GapQuestionOut.of(q) for q in result.pending_gap_questions),
    )
