"""Resume Validator.

Combina a checagem factual deterministica (autoridade) com a auditoria
semantica da IA (complementar). A IA pode ADICIONAR problemas, nunca remover:
se o guard deterministico apontou alucinacao, o resultado e invalido
independentemente do que a IA diga.
"""

from __future__ import annotations

from app.ai.provider import AIProvider, ValidationRequest
from app.job.models import JobAnalysis, MatchReport
from app.job.taxonomy import resolve_canonical
from app.resume.evidence import EvidenceIndex
from app.resume.models import Resume
from app.resume.serialize import job_analysis_to_text, resume_to_text
from app.validation.ats import evaluate_ats
from app.validation.factual_guard import run_factual_guard
from app.validation.models import ValidationIssue, ValidationResult

HALLUCINATION_PENALTY = 30
UNSUPPORTED_PENALTY = 8


def _clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return max(minimum, min(maximum, round(value)))


def _confirmed_terms_in_index(index: EvidenceIndex) -> tuple[str, ...]:
    """Termos que só existem no índice por confirmação da pessoa (regra 2,
    `app.job.confirmations`) — não fazem parte do texto literal do
    currículo base, então precisam ser informados à IA separadamente."""
    return tuple(
        sorted(term for term, evidence in index.by_term.items() if "confirmed" in evidence.sources)
    )


async def validate_adaptation(
    *,
    base: Resume,
    adapted: Resume,
    index: EvidenceIndex,
    analysis: JobAnalysis,
    match: MatchReport,
    provider: AIProvider,
) -> ValidationResult:
    guard = run_factual_guard(adapted, index)
    ats = evaluate_ats(adapted)

    hallucinations: list[ValidationIssue] = [
        ValidationIssue(
            value=finding.value,
            location=finding.location,
            reason=finding.reason,
            source="deterministic",
        )
        for finding in guard.hallucinations
    ]
    unsupported: list[ValidationIssue] = [
        ValidationIssue(
            value=finding.value,
            location=finding.location,
            reason=finding.reason,
            source="deterministic",
        )
        for finding in guard.unsupported_claims
    ]

    recommendations: list[str] = []
    missing_relevant: set[str] = set()
    job_alignment: float = match.job_match_score
    validator = "deterministic"

    try:
        base_resume_text = resume_to_text(base)
        confirmed = _confirmed_terms_in_index(index)
        if confirmed:
            # A IA compara texto-a-texto e não conhece o índice de evidências;
            # sem isto, ela sinalizaria como alucinação um termo que a PESSOA
            # confirmou explicitamente (regra 2) e que o guard determinístico
            # já aceita.
            base_resume_text += (
                "\n\nCONFIRMADO PELO USUÁRIO PARA ESTA VAGA (não inventado, resposta explícita "
                "a uma pergunta de gap): " + ", ".join(confirmed)
            )

        ai_result = await provider.validate_resume(
            ValidationRequest(
                base_resume_text=base_resume_text,
                job_analysis_text=job_analysis_to_text(analysis),
                adapted_resume_text=resume_to_text(adapted),
            )
        )
        # O provider heuristico nao e IA: so rotula como "+ai" quando remoto.
        validator = "deterministic+ai" if provider.is_remote else "deterministic"

        # A IA pode apontar alucinacao que o guard nao pegou (ex.: cargo inventado).
        for issue in ai_result.hallucinations:
            hallucinations.append(
                ValidationIssue(
                    value=issue.value,
                    location=issue.location or "Currículo adaptado",
                    reason=issue.reason or "Sinalizado pelo validador de IA.",
                    source="ai",
                )
            )
        for issue in ai_result.unsupported_claims:
            unsupported.append(
                ValidationIssue(
                    value=issue.value,
                    location=issue.location or "Currículo adaptado",
                    reason=issue.reason or "Afirmação sem respaldo no currículo base.",
                    source="ai",
                )
            )
        for keyword in ai_result.missing_relevant_keywords:
            canonical = resolve_canonical(keyword) or keyword
            # So e "keyword faltante" se houver evidencia real; senao e gap.
            if index.has_any_evidence(canonical):
                missing_relevant.add(canonical)

        recommendations.extend(ai_result.recommendations)
        job_alignment = (match.job_match_score + ai_result.job_alignment) / 2
    except Exception as error:  # noqa: BLE001 - degradacao controlada
        recommendations.append(
            f"Validação semântica por IA indisponível ({error}). "
            "A validação factual determinística foi aplicada integralmente."
        )

    # Keywords com evidencia real exigidas pela vaga e ausentes do adaptado.
    adapted_text = resume_to_text(adapted).lower()
    for requirement in analysis.requirements:
        if not index.has_any_evidence(requirement.term):
            continue
        if requirement.term.lower() in adapted_text:
            continue
        missing_relevant.add(requirement.term)

    factual_score = _clamp(
        100
        - len(hallucinations) * HALLUCINATION_PENALTY
        - len(unsupported) * UNSUPPORTED_PENALTY
    )
    is_valid = not hallucinations and not unsupported

    if not is_valid:
        recommendations.insert(
            0,
            "Geração de PDF bloqueada: há informação no currículo adaptado sem "
            "respaldo no currículo base.",
        )
    # Lacunas: sem evidencia direta (NONE) ou apenas conceito relacionado (WEAK).
    # Ambos sao reportados e nenhum e adicionado ao curriculo.
    for gap in (*match.missing, *match.weak)[:6]:
        detail = (
            f" (apenas conceito relacionado a {gap.related_via})" if gap.related_via else ""
        )
        recommendations.append(
            f"GAP: {gap.term} não identificado no currículo base{detail} — "
            "não foi adicionado ao currículo."
        )

    return ValidationResult(
        is_valid=is_valid,
        score=_clamp((factual_score + ats.score + job_alignment) / 3),
        hallucinations=tuple(hallucinations),
        unsupported_claims=tuple(unsupported),
        missing_relevant_keywords=tuple(sorted(missing_relevant)),
        overused_keywords=ats.overused_keywords,
        factual_consistency=not hallucinations,
        ats_quality=ats.score,
        job_alignment=_clamp(job_alignment),
        recommendations=tuple(dict.fromkeys(recommendations))[:10],
        ats_checks=ats.checks,
        validator=validator,
    )
