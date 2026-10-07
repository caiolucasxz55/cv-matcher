"""Pipeline do "CV Matcher Novo" — mesmo fluxo de
`app.pipeline.run_version_pipeline`, mas usando o adaptador que CURA as
habilidades pela categoria dominante da vaga (`app.resume.focused_adapt`)
em vez do adaptador oficial, que nunca remove nada declarado no currículo
base.

Duplicado deliberadamente a partir de `run_version_pipeline` — pedido
explícito: rodar as duas versões lado a lado em vagas reais e comparar qual
traz mais retorno, sem arriscar o fluxo "oficial" já testado (regra 9).
Reaproveita as peças que não mudam (análise da vaga, índice de evidências,
recomendação entre as 3 variantes) em vez de duplicá-las.
"""

from __future__ import annotations

from app.ai.factory import get_ai_provider
from app.ai.provider import AdaptationRequest, AIProvider
from app.job.confirmations import SkillConfirmation, confirmed_terms, pending_gap_questions
from app.job.models import JobInput
from app.pdf.filename import build_pdf_filename
from app.pipeline import (
    MAX_VALIDATION_ROUNDS,
    STRATEGIES,
    VariantResult,
    VersionResult,
    _analyze_job,
    _effective_index,
    _recommend_best_variant,
)
from app.resume.adapt import AdaptationEmphasis, AdaptationStrategy, ResumeAdaptation
from app.resume.evidence import EvidenceIndex
from app.resume.focused_adapt import adapt_resume_focused
from app.resume.models import Resume
from app.resume.skills_store import get_base_resume
from app.resume.summary_builder import (
    build_summary_options,
    recommend_adaptation,
    select_summary_option,
)
from app.validation.auto_fix import auto_fix
from app.validation.validate import validate_adaptation


async def _build_focused_variant(
    *,
    base: Resume,
    index: EvidenceIndex,
    analysis,
    match,
    provider: AIProvider,
    emphasis: AdaptationEmphasis,
    strategy: AdaptationStrategy,
    summary_override: str | None,
    confirmed: tuple[str, ...],
) -> VariantResult:
    adaptation = adapt_resume_focused(
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


async def run_focused_version_pipeline(
    job: JobInput,
    *,
    archetype_id: str | None = None,
    summary_option_id: str | None = None,
    provider: AIProvider | None = None,
    base: Resume | None = None,
    confirmations: tuple[SkillConfirmation, ...] = (),
) -> VersionResult:
    """Cria as TRÊS variantes do "CV Matcher Novo" para a vaga — mesma
    forma de `run_version_pipeline`, habilidades curadas pela categoria
    dominante em vez de só reordenadas."""
    base = base or get_base_resume()
    provider = provider or get_ai_provider()

    base_snapshot = base.model_dump_json()
    index = _effective_index(base, confirmations)
    confirmed = confirmed_terms(confirmations)

    analysis, match = await _analyze_job(job, provider, index)
    recommendation = recommend_adaptation(base=base, analysis=analysis, match=match, index=index)

    chosen_archetype = archetype_id or recommendation.detected_archetype
    summary_options = ()
    if chosen_archetype:
        summary_options = tuple(build_summary_options(chosen_archetype, index, match.relevance))

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
        variants[strategy] = await _build_focused_variant(
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
