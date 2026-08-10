from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.factory import get_ai_provider
from app.config import get_settings
from app.job.confirmations import ConfirmationAnswer, GapQuestion, SkillConfirmation
from app.job.models import JobAnalysis, JobInput, MatchReport, TermMatch
from app.pipeline import (
    AnalysisResult,
    RecomputeResult,
    VersionResult,
    run_analysis_pipeline,
    run_recompute_pipeline,
    run_version_pipeline,
)
from app.resume.adapt import STRATEGY_LABELS, AdaptationStrategy
from app.resume.models import Resume
from app.validation.models import ValidationResult
from app.versions import VersionRecord, list_versions

logger = logging.getLogger(__name__)
router = APIRouter(tags=["cv-matcher"])

_settings = get_settings()


# --------------------------------------------------------------------- entrada


class SkillConfirmationIn(BaseModel):
    """Resposta da pessoa a uma pergunta de gap (regra 2)."""

    term: str = Field(min_length=1, max_length=80)
    answer: ConfirmationAnswer
    context: str = Field(default="", max_length=400)

    def to_domain(self) -> SkillConfirmation:
        return SkillConfirmation(term=self.term, answer=self.answer, context=self.context)


class JobPayload(BaseModel):
    description: str = Field(
        min_length=_settings.min_description_length,
        max_length=_settings.max_description_length,
        description="Descrição completa da vaga.",
    )
    company: str | None = Field(default=None, max_length=160)
    job_title: str | None = Field(default=None, max_length=160)
    #: Respostas já dadas às perguntas de gap desta vaga (regra 2).
    confirmations: tuple[SkillConfirmationIn, ...] = ()

    def to_job_input(self) -> JobInput:
        return JobInput(
            description=self.description, company=self.company, job_title=self.job_title
        )

    def to_confirmations(self) -> tuple[SkillConfirmation, ...]:
        return tuple(item.to_domain() for item in self.confirmations)


class CreateVersionPayload(JobPayload):
    """Permite refazer a geração com outro arquétipo ou outra redação."""

    archetype_id: str | None = Field(default=None, max_length=40)
    #: Trava a MESMA redação de resumo nas 3 estratégias (ver `select_summary_option`).
    summary_option_id: str | None = Field(default=None, max_length=60)


# ---------------------------------------------------------------------- saida


class MatchSummary(BaseModel):
    job_match_score: int
    strong: tuple[TermMatch, ...]
    medium: tuple[TermMatch, ...]
    weak: tuple[TermMatch, ...]
    missing: tuple[TermMatch, ...]

    @classmethod
    def of(cls, result: AnalysisResult | VersionResult | RecomputeResult) -> "MatchSummary":
        match = result.match
        return cls(
            job_match_score=match.job_match_score,
            strong=match.strong,
            medium=match.medium,
            weak=match.weak,
            missing=match.missing,
        )


class GapQuestionOut(BaseModel):
    term: str
    category: str
    kind: str
    answer: ConfirmationAnswer | None

    @classmethod
    def of(cls, question: GapQuestion) -> "GapQuestionOut":
        return cls(
            term=question.term, category=question.category, kind=question.kind,
            answer=question.answer,
        )


class RevalidatePayload(BaseModel):
    """Reavalia um currículo editado manualmente (ex.: habilidades ajustadas na
    tela de revisão). Recalcula match, validação e recomendação juntos —
    nunca só a validação isolada (regra 12)."""

    resume: Resume
    analysis: JobAnalysis
    confirmations: tuple[SkillConfirmationIn, ...] = ()

    def to_confirmations(self) -> tuple[SkillConfirmation, ...]:
        return tuple(item.to_domain() for item in self.confirmations)


class ArchetypeScoreOut(BaseModel):
    archetype_id: str
    label: str
    description: str
    score: float
    matched_signals: tuple[str, ...]


class RecommendationOut(BaseModel):
    recommended: bool
    detected_archetype: str | None
    archetype_label: str | None
    reasons: tuple[str, ...]
    ranking: tuple[ArchetypeScoreOut, ...]

    @classmethod
    def of(cls, recommendation) -> "RecommendationOut":  # noqa: ANN001
        return cls(
            recommended=recommendation.recommended,
            detected_archetype=recommendation.detected_archetype,
            archetype_label=recommendation.archetype_label,
            reasons=recommendation.reasons,
            ranking=tuple(ArchetypeScoreOut(**item.__dict__) for item in recommendation.ranking),
        )


class BestVariantOut(BaseModel):
    strategy: AdaptationStrategy
    label: str
    reason: str


class AnalyzeResponse(BaseModel):
    """Diagnóstico do currículo BASE. Nenhuma adaptação foi feita."""

    analysis: JobAnalysis
    match: MatchSummary
    base_resume: Resume
    validation: ValidationResult
    recommendation: RecommendationOut
    pending_gap_questions: tuple[GapQuestionOut, ...]
    pdf_filename: str
    provider_name: str


class SummaryOptionOut(BaseModel):
    id: str
    label: str
    archetype_id: str
    archetype_label: str
    text: str
    techs: tuple[str, ...]


class VariantOut(BaseModel):
    strategy: AdaptationStrategy
    strategy_label: str
    version_label: str
    version_number: int
    created_at: str
    base_version: str
    change_log: tuple[str, ...]
    summary_option_id: str | None
    resume: Resume
    validation: ValidationResult
    auto_fixes: tuple[str, ...]


class CreateVersionResponse(BaseModel):
    analysis: JobAnalysis
    match: MatchSummary
    balanced: VariantOut
    ats_focus: VariantOut
    experience_focus: VariantOut
    summary_options: tuple[SummaryOptionOut, ...]
    recommendation: RecommendationOut
    best_variant: BestVariantOut
    pdf_filename: str
    provider_name: str
    base_resume_untouched: bool
    pending_gap_questions: tuple[GapQuestionOut, ...]


class RevalidateResponse(BaseModel):
    """Regra 12: tudo que o botão "Reanalisar" recalcula junto."""

    match: MatchSummary
    validation: ValidationResult
    recommendation: RecommendationOut
    pending_gap_questions: tuple[GapQuestionOut, ...]


# -------------------------------------------------------------------- rotas


def _to_variant(variant) -> VariantOut:  # noqa: ANN001
    adaptation = variant.adaptation
    return VariantOut(
        strategy=variant.strategy,
        strategy_label=STRATEGY_LABELS[variant.strategy],
        version_label=adaptation.version_label,
        version_number=adaptation.version_number,
        created_at=adaptation.created_at,
        base_version=adaptation.base_version,
        change_log=adaptation.change_log,
        summary_option_id=adaptation.summary_option_id,
        resume=adaptation.resume,
        validation=variant.validation,
        auto_fixes=variant.auto_fixes,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(payload: JobPayload) -> AnalyzeResponse:
    """Avalia se o currículo base (+ confirmações) atende a vaga. Não adapta nada."""
    try:
        result = await run_analysis_pipeline(
            payload.to_job_input(), confirmations=payload.to_confirmations()
        )
    except Exception:  # noqa: BLE001
        logger.exception("Falha na análise da vaga")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível analisar a vaga. Tente novamente.",
        ) from None

    return AnalyzeResponse(
        analysis=result.analysis,
        match=MatchSummary.of(result),
        base_resume=result.base_resume,
        validation=result.validation,
        recommendation=RecommendationOut.of(result.recommendation),
        pending_gap_questions=tuple(GapQuestionOut.of(q) for q in result.pending_gap_questions),
        pdf_filename=result.pdf_filename,
        provider_name=result.provider_name,
    )


@router.post("/versions", response_model=CreateVersionResponse)
async def create_version(payload: CreateVersionPayload) -> CreateVersionResponse:
    """Cria as TRÊS variantes do currículo adaptado para a vaga (regra 9)."""
    try:
        result = await run_version_pipeline(
            payload.to_job_input(),
            archetype_id=payload.archetype_id,
            summary_option_id=payload.summary_option_id,
            confirmations=payload.to_confirmations(),
        )
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao criar a versão adaptada")
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


@router.post("/revalidate", response_model=RevalidateResponse)
async def revalidate(payload: RevalidatePayload) -> RevalidateResponse:
    """Botão "Reanalisar" (regra 12): recalcula match, validação e
    recomendação juntos a partir do currículo editado — nunca só a
    validação isolada."""
    try:
        result = await run_recompute_pipeline(
            resume=payload.resume,
            analysis=payload.analysis,
            confirmations=payload.to_confirmations(),
        )
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao reanalisar o currículo")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível reanalisar o currículo. Tente novamente.",
        ) from None

    return RevalidateResponse(
        match=MatchSummary.of(result),
        validation=result.validation,
        recommendation=RecommendationOut.of(result.recommendation),
        pending_gap_questions=tuple(GapQuestionOut.of(q) for q in result.pending_gap_questions),
    )


@router.get("/versions", response_model=list[VersionRecord])
async def versions() -> list[VersionRecord]:
    """Histórico de versões geradas (apenas metadados, em memória)."""
    return list_versions()
