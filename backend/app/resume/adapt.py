"""Resume Adapter — reorganizacao deterministica do curriculo base.

Nenhuma palavra nova e inventada: tecnologias vem das habilidades do base,
capacidades e focos vem de `summary_template`, e ambos so entram se houver
evidencia real no indice. A unica excecao controlada sao os termos que a
PESSOA confirmou ter (fluxo de gap confirmation, `app.job.confirmations`) e
que passam a ter evidencia no indice desta chamada — nunca no curriculo base
permanente. Esses termos sao fundidos nas categorias de habilidades ja
existentes (pela taxonomia do termo), nunca numa categoria a parte: no
curriculo final ficam indistinguiveis de uma habilidade original.

Estrategias de adaptacao (regra 9): exatamente tres, cada uma reordenando o
MESMO conteudo de forma diferente. Nenhuma remove ou inventa nada; a
diferenca e o peso de relevancia usado para ordenar e qual redacao de
resumo (dentre as ja aprovadas) e escolhida.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from app.job.matching import score_terms
from app.job.models import JobAnalysis, MatchReport
from app.job.taxonomy import TermCategory, detect_terms, get_category, resolve_canonical
from app.resume.evidence import EvidenceIndex
from app.resume.models import Resume, ResumeExperience, ResumeSkillCategory

MAX_SUMMARY_TECHS = 5
MAX_SUMMARY_CAPABILITIES = 3
MAX_SUMMARY_FOCUS = 4

#: As tres estrategias exigidas pela regra 9. Nada fora desta lista existe.
AdaptationStrategy = Literal["balanced", "ats_focus", "experience_focus"]

STRATEGY_LABELS: dict[AdaptationStrategy, str] = {
    "balanced": "Balanced",
    "ats_focus": "ATS / Keyword Focus",
    "experience_focus": "Experience / Impact Focus",
}

STRATEGY_DESCRIPTIONS: dict[AdaptationStrategy, str] = {
    "balanced": (
        "Equilíbrio entre aderência à vaga e leitura natural — mesma lógica "
        "de reordenação padrão, sem reforço artificial em nenhuma direção."
    ),
    "ats_focus": (
        "Prioriza a cobertura literal das palavras-chave obrigatórias e dos "
        "termos de ATS da vaga, no resumo e na ordem das habilidades."
    ),
    "experience_focus": (
        "Prioriza bullets de experiência com resultado concreto já descrito "
        "e comprovação profissional real, não apenas menção em habilidades."
    ),
}

#: Categorias-alvo padrao do curriculo base (`app.resume.base_resume`), usadas
#: para fundir termos confirmados sem criar uma categoria a parte.
_FRONTEND_TECH_TERMS = {
    "TypeScript",
    "JavaScript",
    "React",
    "Next.js",
    "Angular",
    "Vue",
    "Svelte",
    "Tailwind CSS",
}
_TARGET_CATEGORY_BY_TERM_CATEGORY: dict[TermCategory, str] = {
    "database": "skills-data",
    "ai_ml": "skills-ai",
    "cloud": "skills-cloud",
    "devops": "skills-cloud",
    "tool": "skills-eng",
    "competency": "skills-eng",
}
_DEFAULT_CODE_CATEGORY_ID = "skills-backend"


@dataclass(frozen=True)
class AdaptationEmphasis:
    """Hints de ordenacao vindos da IA. Nunca adicionam conteudo."""

    prioritize_terms: tuple[str, ...] = ()
    deprioritize_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResumeAdaptation:
    id: str
    version_number: int
    version_label: str
    created_at: str
    base_version: str
    company: str
    job_title: str
    resume: Resume
    change_log: tuple[str, ...] = field(default=())
    strategy: AdaptationStrategy = "balanced"
    summary_option_id: str | None = None


_version_counter = itertools.count(1)


def reset_version_counter() -> None:
    """Reseta o contador de versoes (usado apenas em testes)."""
    global _version_counter
    _version_counter = itertools.count(1)


def _join_with_and(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} e {items[-1]}"


def build_adapted_summary(
    base: Resume, index: EvidenceIndex, relevance: dict[str, float]
) -> str:
    """Recompoe o resumo a partir de fragmentos aprovados, reordenados pela vaga."""
    template = base.summary_template

    ranked: list[tuple[float, int, str]] = []
    position = 0
    for category in base.skill_categories:
        for item in category.items:
            canonical = resolve_canonical(item) or item
            if not index.has_any_evidence(canonical):
                position += 1
                continue
            score = relevance.get(canonical, 0.0) * 10 + (
                2 if index.has_professional_evidence(canonical) else 0
            )
            if score > 0:
                ranked.append((-score, position, item))
            position += 1

    ranked.sort()
    techs = [item for _, _, item in ranked[:MAX_SUMMARY_TECHS]]

    # Sem nenhuma tecnologia relevante, usa o texto de fallback do curriculo base.
    if not techs:
        return template.fallback

    scored_caps = [
        (-score_terms(fragment.terms, relevance), i, fragment)
        for i, fragment in enumerate(template.capabilities)
        if any(index.has_any_evidence(term) for term in fragment.terms)
    ]
    scored_caps.sort()
    capabilities = [
        fragment.text
        for rank, (neg_score, _, fragment) in enumerate(scored_caps)
        if (neg_score < 0 or rank < 2)
    ][:MAX_SUMMARY_CAPABILITIES]

    scored_focus = [
        (-score_terms(fragment.terms, relevance), i, fragment)
        for i, fragment in enumerate(template.focus)
        if any(index.has_any_evidence(term) for term in fragment.terms)
    ]
    scored_focus.sort()
    focus = [fragment.text for _, _, fragment in scored_focus[:MAX_SUMMARY_FOCUS]]

    sentences = [f"{template.role} {template.opening} {_join_with_and(techs)}."]
    if capabilities:
        sentences.append(f"Experiência em {_join_with_and(capabilities)}.")
    if focus:
        sentences.append(f"Atuação com foco em {_join_with_and(focus)}.")
    return " ".join(sentences)


def _reorder_experience(
    experiences: tuple[ResumeExperience, ...],
    relevance: dict[str, float],
    emphasis: AdaptationEmphasis,
) -> tuple[tuple[ResumeExperience, ...], list[str]]:
    changes: list[str] = []
    boost = {c for c in (resolve_canonical(t) for t in emphasis.prioritize_terms) if c}
    penalize = {c for c in (resolve_canonical(t) for t in emphasis.deprioritize_terms) if c}

    adapted: list[ResumeExperience] = []
    for experience in experiences:
        scored: list[tuple[float, int, object]] = []
        for position, bullet in enumerate(experience.bullets):
            terms = set(bullet.terms)
            terms.update(item.canonical for item in detect_terms(bullet.text))
            score = score_terms(terms, relevance)
            score += 0.5 * len(terms & boost)
            score -= 0.3 * len(terms & penalize)
            scored.append((-score, position, bullet))

        scored.sort(key=lambda entry: (entry[0], entry[1]))
        reordered = tuple(entry[2] for entry in scored)  # type: ignore[misc]

        if any(new.id != old.id for new, old in zip(reordered, experience.bullets)):
            changes.append(
                f'Bullets de "{experience.role} @ {experience.company}" reordenados '
                "por relevância para a vaga."
            )
        adapted.append(experience.model_copy(update={"bullets": reordered}))

    return tuple(adapted), changes


def _augment_relevance(
    relevance: dict[str, float],
    *,
    analysis: JobAnalysis,
    index: EvidenceIndex,
    strategy: AdaptationStrategy,
) -> dict[str, float]:
    """Pondera a relevancia de acordo com a estrategia. Nunca adiciona termo
    novo — so redistribui peso entre termos que ja tem relevancia > 0 na
    vaga (`match.relevance`), sempre por evidencia real (`index`)."""
    if strategy == "balanced":
        return dict(relevance)

    augmented = dict(relevance)

    if strategy == "ats_focus":
        required = set(analysis.required_skills)
        ats_terms = set(analysis.ats_keywords)
        for term, value in list(augmented.items()):
            bonus = (0.6 if term in required else 0.0) + (0.3 if term in ats_terms else 0.0)
            if bonus:
                augmented[term] = min(1.0, value + bonus)
        return augmented

    if strategy == "experience_focus":
        for term, value in list(augmented.items()):
            if index.has_professional_evidence(term):
                augmented[term] = min(1.0, value + 0.4)
        return augmented

    return augmented


def _target_category_id(term: str) -> str:
    """Categoria do curriculo base onde um termo confirmado deve entrar,
    pela taxonomia do termo — nunca uma categoria nova."""
    if term in _FRONTEND_TECH_TERMS:
        return "skills-frontend"
    category = get_category(term)
    if category in ("language", "framework"):
        return _DEFAULT_CODE_CATEGORY_ID
    return _TARGET_CATEGORY_BY_TERM_CATEGORY.get(category, "skills-eng")


def _merge_confirmed_skills(
    confirmed: tuple[str, ...], categories: tuple[ResumeSkillCategory, ...]
) -> tuple[tuple[ResumeSkillCategory, ...], list[str]]:
    """Funde termos que a PESSOA confirmou ter (fluxo de gap confirmation) nas
    categorias de habilidades ja existentes, pela taxonomia de cada termo.
    Nunca cria uma categoria a parte: no curriculo final o termo aparece
    junto das demais habilidades da categoria, sem nenhuma marcacao especial.
    Termos ja declarados em outra categoria nao sao duplicados."""
    already_listed = {item for category in categories for item in category.items}
    new_by_target: dict[str, list[str]] = {}
    for term in confirmed:
        if term in already_listed:
            continue
        already_listed.add(term)
        new_by_target.setdefault(_target_category_id(term), []).append(term)

    if not new_by_target:
        return categories, []

    changes: list[str] = []
    merged: list[ResumeSkillCategory] = []
    for category in categories:
        added = new_by_target.get(category.id)
        if not added:
            merged.append(category)
            continue
        merged.append(category.model_copy(update={"items": (*category.items, *added)}))
        changes.append(
            f'Habilidade(s) que você confirmou ter incorporada(s) à categoria '
            f'"{category.label}": {", ".join(added)}.'
        )

    return tuple(merged), changes


def _reorder_skills(
    categories: tuple[ResumeSkillCategory, ...], relevance: dict[str, float]
) -> tuple[tuple[ResumeSkillCategory, ...], list[str]]:
    changes: list[str] = []
    entries: list[tuple[float, int, ResumeSkillCategory, bool]] = []

    for index_pos, category in enumerate(categories):
        scored_items = sorted(
            ((-relevance.get(resolve_canonical(item) or item, 0.0), i, item)
             for i, item in enumerate(category.items)),
            key=lambda entry: (entry[0], entry[1]),
        )
        items = tuple(item for _, _, item in scored_items)
        total = sum(-entry[0] for entry in scored_items)
        changed_internally = items != category.items
        entries.append(
            (-total, index_pos, category.model_copy(update={"items": items}), changed_internally)
        )

    entries.sort(key=lambda entry: (entry[0], entry[1]))
    ordered = tuple(entry[2] for entry in entries)

    if any(new.id != old.id for new, old in zip(ordered, categories)):
        changes.append(
            "Categorias de habilidades reordenadas: as mais aderentes à vaga vêm primeiro."
        )
    if any(entry[3] for entry in entries):
        changes.append("Tecnologias reordenadas dentro de cada categoria por aderência à vaga.")

    return ordered, changes


def adapt_resume(
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
    """Produz uma NOVA versao do curriculo adaptada a vaga, numa das 3
    estrategias (regra 9): "balanced", "ats_focus" ou "experience_focus".

    `summary_override`, quando informado, e a redacao de arquetipo ja
    escolhida (pelo pipeline, de acordo com a estrategia) para esta versao;
    na ausencia dela, o resumo e recomposto a partir dos fragmentos
    aprovados do curriculo base.

    `confirmed` sao termos que a PESSOA confirmou ter no fluxo de gap
    confirmation (regra 2) — sao fundidos na categoria de habilidades
    existente que corresponde a taxonomia do termo (ex.: Kubernetes entra em
    "Cloud / DevOps"), nunca numa categoria a parte: no curriculo final ficam
    indistinguiveis das habilidades originais.

    O texto dos bullets, os projetos, a formacao, os cursos, os idiomas e o
    cargo do cabecalho permanecem intocados, e nenhuma habilidade original e
    removida. O curriculo base nunca e mutado (modelos sao `frozen`).
    """
    emphasis = emphasis or AdaptationEmphasis()
    relevance = _augment_relevance(match.relevance, analysis=analysis, index=index, strategy=strategy)
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

    skill_categories, skill_changes = _reorder_skills(base.skill_categories, relevance)
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
        ((-score_terms(course.terms, relevance), position, course)
         for position, course in enumerate(base.courses)),
        key=lambda entry: (entry[0], entry[1]),
    )
    courses = tuple(entry[2] for entry in scored_courses)
    if any(new.id != old.id for new, old in zip(courses, base.courses)):
        change_log.append("Cursos reordenados pelos mais relevantes para a vaga.")

    version_number = next(_version_counter)
    version_label = f"#{version_number:03d}"

    resume = base.model_copy(
        update={
            "id": f"adapted-{strategy}-{version_label}",
            "version": f"ADAPTED-{version_label}",
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
