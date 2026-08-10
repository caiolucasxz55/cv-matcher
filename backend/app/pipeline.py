"""Pipelines da aplicacao.

Tres fluxos distintos:

1. ANALISE (`run_analysis_pipeline`) — funcao essencial do CV Matcher.
   Avalia se o CURRICULO BASE, como ele e (mais confirmacoes de gap ja
   respondidas pela pessoa), atende a vaga. Nada e adaptado aqui: o preview
   mostra o curriculo base puro. Tambem calcula quais perguntas de gap
   ainda estao pendentes (regra 2).

2. CRIACAO DE VERSAO (`run_version_pipeline`) — acionada pelo botao.
   Produz EXATAMENTE tres variantes — balanced, ats_focus, experience_focus
   (regra 9) — e recomenda qual delas serve melhor a vaga (regra 10). Cada
   variante e validada.

3. RECALCULO (`run_recompute_pipeline`) — acionado pelo botao "Reanalisar"
   depois de uma edicao manual na tela de revisao. Recalcula TUDO a partir
   do curriculo editado: match, validacao e recomendacao (regra 12) — nunca
   so a validacao isolada.

O curriculo base e imutavel (modelos `frozen`); a integridade e verificada e
exposta em `base_resume_untouched`. Confirmacoes de gap (regra 2) nunca
alteram o curriculo base — apenas o indice de evidencias usado nesta
chamada e a categoria "Confirmado para esta vaga" das versoes adaptadas.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.factory import get_ai_provider
from app.ai.provider import AdaptationRequest, AIProvider, JobAnalysisRequest
from app.job.analyze import analyze_job_deterministic, merge_ai_signals
from app.job.confirmations import (
    GapQuestion,
    SkillConfirmation,
    apply_confirmations,
    confirmed_terms,
    pending_gap_questions,
)
from app.job.matching import build_match_report
from app.job.models import JobAnalysis, JobInput, MatchReport
from app.pdf.filename import build_pdf_filename
from app.resume.adapt import (
    STRATEGY_LABELS,
    AdaptationEmphasis,
    AdaptationStrategy,
    ResumeAdaptation,
    adapt_resume,
)
from app.resume.evidence import EvidenceIndex, build_evidence_index
from app.resume.models import Resume
from app.resume.skills_store import get_base_resume
from app.resume.summary_builder import (
    AdaptationRecommendation,
    SummaryOption,
    build_summary_options,
    recommend_adaptation,
    select_summary_option,
)
from app.validation.auto_fix import auto_fix
from app.validation.models import ValidationResult
from app.validation.validate import validate_adaptation
from app.versions import VersionRecord, record_version

MAX_VALIDATION_ROUNDS = 2

#: As tres estrategias exigidas pela regra 9 — ordem fixa em toda a API.
STRATEGIES: tuple[AdaptationStrategy, ...] = ("balanced", "ats_focus", "experience_focus")


@dataclass(frozen=True)
class AnalysisResult:
    """Diagnostico do curriculo BASE (+ confirmacoes) contra a vaga."""

    analysis: JobAnalysis
    match: MatchReport
    base_resume: Resume
    validation: ValidationResult
    recommendation: AdaptationRecommendation
    #: Requisitos sem evidencia ainda nao confirmados/negados pela pessoa.
    pending_gap_questions: tuple[GapQuestion, ...]
    pdf_filename: str
    provider_name: str


@dataclass(frozen=True)
class VariantResult:
    strategy: AdaptationStrategy
    adaptation: ResumeAdaptation
    validation: ValidationResult
    auto_fixes: tuple[str, ...]


@dataclass(frozen=True)
class BestVariantRecommendation:
    """Regra 10: qual das 3 versoes recomendar, e por que."""

    strategy: AdaptationStrategy
    label: str
    reason: str


@dataclass(frozen=True)
class VersionResult:
    """As tres variantes (regra 9) + a recomendacao entre elas (regra 10)."""

    analysis: JobAnalysis
    match: MatchReport
    balanced: VariantResult
    ats_focus: VariantResult
    experience_focus: VariantResult
    summary_options: tuple[SummaryOption, ...]
    recommendation: AdaptationRecommendation
    best_variant: BestVariantRecommendation
    pdf_filename: str
    provider_name: str
    base_resume_untouched: bool
    pending_gap_questions: tuple[GapQuestion, ...]

    def variant(self, strategy: AdaptationStrategy) -> VariantResult:
        return {
            "balanced": self.balanced,
            "ats_focus": self.ats_focus,
            "experience_focus": self.experience_focus,
        }[strategy]


@dataclass(frozen=True)
class RecomputeResult:
    """Regra 12: tudo que o botao "Reanalisar" precisa recalcular junto."""

    match: MatchReport
    validation: ValidationResult
    recommendation: AdaptationRecommendation
    pending_gap_questions: tuple[GapQuestion, ...]


async def _analyze_job(
    job: JobInput, provider: AIProvider, index: EvidenceIndex
) -> tuple[JobAnalysis, MatchReport]:
    analysis = analyze_job_deterministic(job)
    try:
        signals = await provider.analyze_job_description(
            JobAnalysisRequest(
                description=job.description, company=job.company, job_title=job.job_title
            )
        )
        analysis = merge_ai_signals(
            analysis,
            seniority=signals.seniority,
            job_title=signals.job_title,
            required_terms=signals.required_terms,
            preferred_terms=signals.preferred_terms,
            responsibilities=signals.responsibilities,
            extra_keywords=signals.extra_keywords,
            notes=signals.notes,
        )
    except Exception as error:  # noqa: BLE001 - degradacao controlada
        analysis = analysis.model_copy(
            update={
                "ai_notes": (
                    f"Análise semântica por IA indisponível ({error}). "
                    "Foi usada a análise determinística.",
                )
            }
        )

    match = build_match_report(analysis, index)
    analysis = analysis.model_copy(
        update={
            "candidate_matches": tuple(item.term for item in (*match.strong, *match.medium)),
            "missing_requirements": tuple(item.term for item in match.missing),
        }
    )
    return analysis, match


def _effective_index(base: Resume, confirmations: tuple[SkillConfirmation, ...]) -> EvidenceIndex:
    """Indice de evidencias desta chamada: base + confirmacoes de gap (regra
    2). Nunca persiste — cada request recalcula do zero."""
    return apply_confirmations(build_evidence_index(base), confirmations)


async def run_analysis_pipeline(
    job: JobInput,
    *,
    provider: AIProvider | None = None,
    base: Resume | None = None,
    confirmations: tuple[SkillConfirmation, ...] = (),
) -> AnalysisResult:
    """Avalia o curriculo BASE (+ confirmacoes) contra a vaga. Nao adapta nada."""
    base = base or get_base_resume()
    provider = provider or get_ai_provider()
    index = _effective_index(base, confirmations)

    analysis, match = await _analyze_job(job, provider, index)

    # Valida o proprio curriculo base — e ele que sera exibido no preview.
    validation = await validate_adaptation(
        base=base,
        adapted=base,
        index=index,
        analysis=analysis,
        match=match,
        provider=provider,
    )

    return AnalysisResult(
        analysis=analysis,
        match=match,
        base_resume=base,
        validation=validation,
        recommendation=recommend_adaptation(
            base=base, analysis=analysis, match=match, index=index
        ),
        pending_gap_questions=pending_gap_questions(match, confirmations),
        pdf_filename=build_pdf_filename(company=analysis.company),
        provider_name=provider.name,
    )


async def _build_variant(
    *,
    base: Resume,
    index: EvidenceIndex,
    analysis: JobAnalysis,
    match: MatchReport,
    provider: AIProvider,
    emphasis: AdaptationEmphasis,
    strategy: AdaptationStrategy,
    summary_override: str | None,
    confirmed: tuple[str, ...],
) -> VariantResult:
    adaptation = adapt_resume(
        base=base,
        index=index,
        analysis=analysis,
        match=match,
        strategy=strategy,
        emphasis=emphasis,
        summary_override=summary_override,
        confirmed=confirmed,
    )

    auto_fixes: list[str] = []
    validation = await validate_adaptation(
        base=base,
        adapted=adaptation.resume,
        index=index,
        analysis=analysis,
        match=match,
        provider=provider,
    )

    round_index = 1
    while round_index < MAX_VALIDATION_ROUNDS and not validation.is_valid:
        fixed = auto_fix(adaptation.resume, base, index)
        if not fixed.applied:
            break
        auto_fixes.extend(fixed.applied)
        adaptation = ResumeAdaptation(**{**adaptation.__dict__, "resume": fixed.resume})
        validation = await validate_adaptation(
            base=base,
            adapted=fixed.resume,
            index=index,
            analysis=analysis,
            match=match,
            provider=provider,
        )
        round_index += 1

    return VariantResult(
        strategy=strategy, adaptation=adaptation, validation=validation, auto_fixes=tuple(auto_fixes)
    )


def _recommend_best_variant(
    variants: dict[AdaptationStrategy, VariantResult],
) -> BestVariantRecommendation:
    """Regra 10 — deterministico, sem IA e sem forcar nada (regra 3): compara
    score composto (`ValidationResult.score`, ja combina consistencia
    factual + ATS + aderencia a vaga), depois ATS e aderencia isoladas como
    desempate. Uma versao invalida (com alucinacao) so e recomendada se
    TODAS forem invalidas."""
    all_variants = list(variants.values())
    valid = [v for v in all_variants if v.validation.is_valid] or all_variants

    valid.sort(
        key=lambda v: (
            -v.validation.score,
            -v.validation.ats_quality,
            -v.validation.job_alignment,
            v.strategy,
        )
    )
    winner = valid[0]

    best_score = max(v.validation.score for v in all_variants)
    best_ats = max(v.validation.ats_quality for v in all_variants)
    best_alignment = max(v.validation.job_alignment for v in all_variants)

    reasons: list[str] = []
    if winner.validation.ats_quality >= best_ats and winner.validation.ats_quality > 0:
        reasons.append("maior compatibilidade com leitores de ATS")
    if winner.validation.job_alignment >= best_alignment:
        reasons.append("maior cobertura dos requisitos e keywords relevantes para a vaga")
    if winner.validation.score >= best_score and not reasons:
        reasons.append("melhor equilíbrio geral entre aderência à vaga e qualidade do currículo")
    if winner.validation.is_valid:
        reasons.append("mantendo consistência total com sua experiência real")

    if len(reasons) > 1:
        reason_text = ", ".join(reasons[:-1]) + " e " + reasons[-1]
    elif reasons:
        reason_text = reasons[0]
    else:
        reason_text = "melhor equilíbrio entre aderência à vaga e consistência factual"

    return BestVariantRecommendation(
        strategy=winner.strategy,
        label=STRATEGY_LABELS[winner.strategy],
        reason=f"Esta versão apresenta {reason_text}.",
    )


async def run_version_pipeline(
    job: JobInput,
    *,
    archetype_id: str | None = None,
    summary_option_id: str | None = None,
    provider: AIProvider | None = None,
    base: Resume | None = None,
    confirmations: tuple[SkillConfirmation, ...] = (),
) -> VersionResult:
    """Cria as TRES variantes do curriculo para a vaga (regra 9).

    `archetype_id` permite trocar o arquetipo detectado manualmente.
    `summary_option_id`, se informado, TRAVA a mesma redacao de resumo nas
    tres estrategias (util para comparar so o efeito da reordenacao); sem
    ele, cada estrategia escolhe a redacao mais adequada a si mesma
    (`select_summary_option`).
    """
    base = base or get_base_resume()
    provider = provider or get_ai_provider()

    base_snapshot = base.model_dump_json()
    index = _effective_index(base, confirmations)
    confirmed = confirmed_terms(confirmations)

    analysis, match = await _analyze_job(job, provider, index)
    recommendation = recommend_adaptation(
        base=base, analysis=analysis, match=match, index=index
    )

    chosen_archetype = archetype_id or recommendation.detected_archetype
    summary_options: tuple[SummaryOption, ...] = ()
    if chosen_archetype:
        summary_options = tuple(
            build_summary_options(chosen_archetype, index, match.relevance)
        )

    forced_option = (
        next((option for option in summary_options if option.id == summary_option_id), None)
        if summary_option_id
        else None
    )

    # Enfase (IA) — apenas hints de ordenacao, nunca conteudo novo.
    emphasis = AdaptationEmphasis()
    try:
        recommended = await provider.recommend_adaptation(
            AdaptationRequest(
                job_title=analysis.job_title,
                company=analysis.company,
                required_terms=analysis.required_skills,
                preferred_terms=analysis.preferred_skills,
                evidenced_terms=tuple(index.by_term.keys()),
            )
        )
        emphasis = AdaptationEmphasis(
            prioritize_terms=tuple(recommended.prioritize_terms),
            deprioritize_terms=tuple(recommended.deprioritize_terms),
        )
    except Exception:  # noqa: BLE001 - enfase e opcional
        pass

    variants: dict[AdaptationStrategy, VariantResult] = {}
    for strategy in STRATEGIES:
        option = forced_option or select_summary_option(
            summary_options, strategy=strategy, analysis=analysis
        )
        variants[strategy] = await _build_variant(
            base=base,
            index=index,
            analysis=analysis,
            match=match,
            provider=provider,
            emphasis=emphasis,
            strategy=strategy,
            summary_override=option.text if option else None,
            confirmed=confirmed,
        )

    pdf_filename = build_pdf_filename(company=analysis.company)

    for strategy, variant in variants.items():
        record_version(
            VersionRecord(
                version_label=variant.adaptation.version_label,
                version_number=variant.adaptation.version_number,
                created_at=variant.adaptation.created_at,
                company=variant.adaptation.company,
                job_title=variant.adaptation.job_title,
                job_match_score=match.job_match_score,
                ats_score=variant.validation.ats_quality,
                is_valid=variant.validation.is_valid,
                pdf_filename=pdf_filename,
                strategy=strategy,
            )
        )

    return VersionResult(
        analysis=analysis,
        match=match,
        balanced=variants["balanced"],
        ats_focus=variants["ats_focus"],
        experience_focus=variants["experience_focus"],
        summary_options=summary_options,
        recommendation=recommendation,
        best_variant=_recommend_best_variant(variants),
        pdf_filename=pdf_filename,
        provider_name=provider.name,
        base_resume_untouched=base.model_dump_json() == base_snapshot,
        pending_gap_questions=pending_gap_questions(match, confirmations),
    )


async def run_recompute_pipeline(
    *,
    resume: Resume,
    analysis: JobAnalysis,
    provider: AIProvider | None = None,
    base: Resume | None = None,
    confirmations: tuple[SkillConfirmation, ...] = (),
) -> RecomputeResult:
    """Regra 12 — botao "Reanalisar": recalcula TUDO a partir do curriculo
    editado manualmente na tela de revisao, nunca so a validacao isolada.

    O indice de evidencias usado para julgar `resume` continua vindo do
    curriculo BASE (+ confirmacoes) — nunca do proprio `resume` editado,
    senao qualquer edicao se autovalidaria trivialmente. Assim, adicionar um
    termo que a base nao sustenta (e que a pessoa nao confirmou) continua
    sendo sinalizado, exatamente como antes da edicao.
    """
    base = base or get_base_resume()
    provider = provider or get_ai_provider()
    index = _effective_index(base, confirmations)

    match = build_match_report(analysis, index)
    validation = await validate_adaptation(
        base=base,
        adapted=resume,
        index=index,
        analysis=analysis,
        match=match,
        provider=provider,
    )
    recommendation = recommend_adaptation(base=base, analysis=analysis, match=match, index=index)

    return RecomputeResult(
        match=match,
        validation=validation,
        recommendation=recommendation,
        pending_gap_questions=pending_gap_questions(match, confirmations),
    )
