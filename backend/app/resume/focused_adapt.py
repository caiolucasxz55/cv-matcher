"""Adaptador EXPERIMENTAL "CV Matcher Novo".

Mesmo contrato de `app.resume.adapt.adapt_resume`, mas com uma diferença
deliberada na seção de habilidades: em vez de reordenar as 6 categorias por
igual (o que deixa o currículo "pulverizado" — um pouco de tudo, sem foco
claro), aqui a categoria que corresponde ao arquétipo detectado da vaga
(ex.: Backend, para uma vaga Python/FastAPI) é mantida por inteiro, e as
DEMAIS categorias são cortadas para poucos itens.

Isso quebra uma garantia do motor "oficial" (`app.resume.adapt`): lá,
nenhuma habilidade original é removida de uma versão adaptada — aqui, pode
ser. Nada é INVENTADO (nenhum item novo aparece — a mesma garantia de
sempre), mas a composição final pode omitir itens que o currículo base
declara. É uma escolha explícita, pedida para comparar lado a lado com o
motor oficial em vagas reais e ver qual traz mais retorno — por isso este
módulo vive separado de `app.resume.adapt`, sem alterar o fluxo "oficial"
já testado (regra 9) em nada.

Reaproveita a MESMA detecção determinística de arquétipo já usada para
recomendar redações de resumo (`app.resume.summary_builder.score_archetypes`)
para decidir qual categoria é a dominante — nenhuma heurística nova.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.job.models import JobAnalysis, MatchReport
from app.job.taxonomy import detect_terms, resolve_canonical
from app.resume.adapt import (
    AdaptationEmphasis,
    AdaptationStrategy,
    ResumeAdaptation,
    _augment_relevance,
    _merge_confirmed_skills,
    _reorder_experience,
    _version_counter,
    build_adapted_summary,
)
from app.job.matching import score_terms
from app.resume.evidence import EvidenceIndex
from app.resume.models import Resume, ResumeSkillCategory
from app.resume.summary_builder import score_archetypes

#: Máximo de itens mantidos numa categoria que NÃO é a dominante da vaga.
MAX_SECONDARY_ITEMS = 2

#: Categoria(s) de habilidades que cada arquétipo detectado preenche por
#: inteiro (ids de `app.resume.base_resume`). "fullstack" mantém as duas
#: (frontend + backend) cheias — não existe categoria "Dados" aqui porque
#: também não existe arquétipo de Dados (ver `archetypes.py`).
_DOMINANT_CATEGORIES_BY_ARCHETYPE: dict[str, tuple[str, ...]] = {
    "frontend": ("skills-frontend",),
    "backend": ("skills-backend",),
    "fullstack": ("skills-frontend", "skills-backend"),
    "devops": ("skills-cloud",),
    "ai_ml": ("skills-ai",),
}


def detect_dominant_category_ids(
    analysis: JobAnalysis, match: MatchReport, index: EvidenceIndex
) -> tuple[str, ...]:
    """Categoria(s) de habilidade que devem ficar cheias nesta vaga. Sem
    arquétipo com evidência real (score 0), não há dominante — quem chama
    deve cair no comportamento padrão (sem corte nenhum)."""
    ranking = score_archetypes(analysis, match, index)
    top = ranking[0] if ranking else None
    if top is None or top.score == 0:
        return ()
    return _DOMINANT_CATEGORIES_BY_ARCHETYPE.get(top.archetype_id, ())


def _sorted_items(category: ResumeSkillCategory, relevance: dict[str, float]) -> list[str]:
    scored = sorted(
        (
            (-relevance.get(resolve_canonical(item) or item, 0.0), position, item)
            for position, item in enumerate(category.items)
        ),
        key=lambda entry: (entry[0], entry[1]),
    )
    return [item for _, _, item in scored]


def focus_skills(
    categories: tuple[ResumeSkillCategory, ...],
    relevance: dict[str, float],
    dominant_ids: tuple[str, ...],
) -> tuple[tuple[ResumeSkillCategory, ...], list[str]]:
    """Mantém a(s) categoria(s) dominante(s) inteira(s), na frente, e corta
    as demais para no máximo `MAX_SECONDARY_ITEMS` (os de maior relevância
    primeiro; empate preserva a ordem original — é assim que tecnologias
    "padrão" sem relevância direta para a vaga ainda aparecem, só que
    poucas, em vez de sumirem por completo)."""
    if not dominant_ids:
        # Sem arquétipo detectado com evidência: comportamento padrão do
        # motor oficial, sem corte (reordena, nunca remove).
        ordered = tuple(
            category.model_copy(update={"items": tuple(_sorted_items(category, relevance))})
            for category in categories
        )
        return ordered, []

    changes: list[str] = []
    dominant: list[ResumeSkillCategory] = []
    secondary: list[ResumeSkillCategory] = []
    for category in categories:
        items = _sorted_items(category, relevance)
        if category.id in dominant_ids:
            dominant.append(category.model_copy(update={"items": tuple(items)}))
            continue
        kept = tuple(items[:MAX_SECONDARY_ITEMS])
        if len(kept) < len(category.items):
            changes.append(
                f'Categoria "{category.label}" reduzida a {len(kept)} '
                f"habilidade(s) ({', '.join(kept)}) para focar o currículo no "
                "perfil desta vaga."
            )
        secondary.append(category.model_copy(update={"items": kept}))

    if dominant:
        changes.insert(
            0,
            "Categoria(s) "
            + ", ".join(f'"{category.label}"' for category in dominant)
            + " mantida(s) por inteiro: é o foco identificado para esta vaga.",
        )

    return (*dominant, *secondary), changes


def adapt_resume_focused(
    *,
    base: Resume,
    index: EvidenceIndex,
    analysis: JobAnalysis,
    match: MatchReport,
    strategy: AdaptationStrategy = "balanced",
    emphasis: AdaptationEmphasis | None = None,
    summary_override: str | None = None,
    confirmed: tuple[str, ...] = (),
) -> ResumeAdaptation:
    """Mesmo contrato de `app.resume.adapt.adapt_resume` — a diferença é só
    em `focus_skills` (ver docstring do módulo): a seção de habilidades é
    CURADA pela categoria dominante da vaga, não apenas reordenada."""
    emphasis = emphasis or AdaptationEmphasis()
    relevance = _augment_relevance(
        match.relevance, analysis=analysis, index=index, strategy=strategy
    )
    change_log: list[str] = []

    if summary_override is not None:
        summary = summary_override
        change_log.append("Resumo profissional substituído pela redação escolhida.")
    else:
        summary = build_adapted_summary(base, index, relevance)
        if summary != base.summary:
            change_log.append(
                "Resumo profissional recomposto com ênfase nas tecnologias exigidas pela vaga."
            )

    experience, experience_changes = _reorder_experience(base.experience, relevance, emphasis)
    change_log.extend(experience_changes)

    dominant_ids = detect_dominant_category_ids(analysis, match, index)
    skill_categories, skill_changes = focus_skills(base.skill_categories, relevance, dominant_ids)
    change_log.extend(skill_changes)

    skill_categories, confirmed_changes = _merge_confirmed_skills(confirmed, skill_categories)
    change_log.extend(confirmed_changes)

    scored_projects = []
    for position, project in enumerate(base.projects):
        terms = set(project.terms)
        terms.update(
            item.canonical for item in detect_terms(f"{project.name} {project.description}")
        )
        for bullet in project.bullets:
            terms.update(bullet.terms)
            terms.update(item.canonical for item in detect_terms(bullet.text))
        scored_projects.append((-score_terms(terms, relevance), position, project))
    scored_projects.sort(key=lambda entry: (entry[0], entry[1]))
    projects = tuple(entry[2] for entry in scored_projects)

    scored_courses = sorted(
        (
            (-score_terms(course.terms, relevance), position, course)
            for position, course in enumerate(base.courses)
        ),
        key=lambda entry: (entry[0], entry[1]),
    )
    courses = tuple(entry[2] for entry in scored_courses)
    if any(new.id != old.id for new, old in zip(courses, base.courses)):
        change_log.append("Cursos reordenados pelos mais relevantes para a vaga.")

    version_number = next(_version_counter)
    version_label = f"#{version_number:03d}"

    resume = base.model_copy(
        update={
            "id": f"focused-{strategy}-{version_label}",
            "version": f"FOCUSED-{version_label}",
            "kind": "adapted",
            "summary": summary,
            "experience": experience,
            "skill_categories": skill_categories,
            "projects": projects,
            "courses": courses,
        }
    )

    return ResumeAdaptation(
        id=resume.id,
        version_number=version_number,
        version_label=version_label,
        created_at=datetime.now(timezone.utc).isoformat(),
        base_version=base.version,
        company=analysis.company,
        job_title=analysis.job_title,
        resume=resume,
        change_log=tuple(change_log),
        strategy=strategy,
    )
