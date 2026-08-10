"""Auto-correcao de problemas PERMITIDOS.

O unico tipo de correcao automatica autorizada e a REMOCAO de conteudo sem
respaldo. O sistema nunca adiciona informacao para "consertar" o curriculo.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.job.taxonomy import resolve_canonical
from app.resume.evidence import EvidenceIndex
from app.resume.models import Resume
from app.validation.factual_guard import run_factual_guard


@dataclass(frozen=True)
class AutoFixResult:
    resume: Resume
    applied: tuple[str, ...]


def auto_fix(adapted: Resume, base: Resume, index: EvidenceIndex) -> AutoFixResult:
    guard = run_factual_guard(adapted, index)
    if guard.ok:
        return AutoFixResult(adapted, ())

    applied: list[str] = []
    result = adapted

    # 1. Remover itens de habilidades sem evidencia no curriculo base.
    cleaned_categories = []
    for category in result.skill_categories:
        kept = tuple(
            item
            for item in category.items
            if index.has_any_evidence(resolve_canonical(item) or item)
        )
        if len(kept) != len(category.items):
            removed = [item for item in category.items if item not in kept]
            applied.append(
                f'Removidas de "{category.label}" tecnologias sem evidência no '
                f"currículo base: {', '.join(removed)}."
            )
        if kept:
            cleaned_categories.append(category.model_copy(update={"items": kept}))
    result = result.model_copy(update={"skill_categories": tuple(cleaned_categories)})

    # 2. Restaurar o resumo profissional do base se o adaptado falhar.
    summary_findings = [
        finding
        for finding in (*guard.hallucinations, *guard.unsupported_claims)
        if finding.location.startswith("Resumo")
    ]
    if summary_findings:
        result = result.model_copy(update={"summary": base.summary})
        applied.append(
            "Resumo profissional revertido para a redação original do currículo base."
        )

    # 3. Restaurar bullets alterados: a adaptacao so reordena, entao qualquer
    #    divergencia textual e restaurada a partir do base.
    base_bullets = {
        bullet.id: bullet.text
        for experience in base.experience
        for bullet in experience.bullets
    }
    restored = 0
    restored_experience = []
    for experience in result.experience:
        bullets = []
        for bullet in experience.bullets:
            original = base_bullets.get(bullet.id)
            if original is not None and original != bullet.text:
                restored += 1
                bullets.append(bullet.model_copy(update={"text": original}))
            else:
                bullets.append(bullet)
        restored_experience.append(experience.model_copy(update={"bullets": tuple(bullets)}))
    if restored:
        result = result.model_copy(update={"experience": tuple(restored_experience)})
        applied.append(
            f"{restored} bullet(s) de experiência restaurado(s) ao texto original."
        )

    return AutoFixResult(result, tuple(applied))
