"""Deteccao de arquetipo e montagem das redacoes de resumo.

Nenhum texto e gerado: as redacoes vem prontas de `archetypes.py` (dado do
autor) e o marcador {techs} e preenchido apenas com tecnologias que tem
evidencia real no curriculo base.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.job.models import JobAnalysis, MatchReport
from app.resume.archetypes import ARCHETYPES, Archetype, get_archetype
from app.resume.evidence import EvidenceIndex
from app.resume.models import Resume

MIN_TECHS = 2
MAX_TECHS = 5


@dataclass(frozen=True)
class SummaryOption:
    id: str
    label: str
    archetype_id: str
    archetype_label: str
    text: str
    #: Tecnologias que entraram na redação (todas com evidência).
    techs: tuple[str, ...]


@dataclass(frozen=True)
class ArchetypeScore:
    archetype_id: str
    label: str
    description: str
    score: float
    #: Sinais da vaga que ativaram este arquétipo.
    matched_signals: tuple[str, ...]


def _join_with_and(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} e {items[-1]}"


def score_archetypes(
    analysis: JobAnalysis, match: MatchReport, index: EvidenceIndex
) -> list[ArchetypeScore]:
    """Pontua cada arquetipo contra os termos da vaga.

    Peso: requisito obrigatorio vale mais que desejavel, e um sinal so conta se
    o candidato tiver evidencia dele — a vaga pedir Kubernetes nao torna o
    perfil DevOps mais forte se o candidato nao tem Kubernetes.
    """
    job_terms = set(analysis.keywords)
    required = set(analysis.required_skills)

    scored: list[ArchetypeScore] = []
    for archetype in ARCHETYPES:
        matched: list[str] = []
        score = 0.0
        for signal in archetype.signals:
            if signal not in job_terms:
                continue
            matched.append(signal)
            if not index.has_any_evidence(signal):
                continue  # a vaga pede, mas o candidato nao tem: nao pontua
            weight = 2.0 if signal in required else 1.0
            if index.has_professional_evidence(signal):
                weight *= 1.5
            score += weight

        scored.append(
            ArchetypeScore(
                archetype_id=archetype.id,
                label=archetype.label,
                description=archetype.description,
                score=round(score, 2),
                matched_signals=tuple(matched),
            )
        )

    scored.sort(key=lambda item: (-item.score, item.archetype_id))
    return scored


def _select_techs(
    archetype: Archetype, index: EvidenceIndex, relevance: dict[str, float]
) -> list[str]:
    candidates: list[tuple[float, int, str]] = []
    for position, tech in enumerate(archetype.tech_pool):
        if not index.has_any_evidence(tech):
            continue  # regra absoluta: sem evidencia, fora
        bonus = 0.5 if index.has_professional_evidence(tech) else 0.0
        candidates.append((-(relevance.get(tech, 0.0) + bonus), position, tech))

    candidates.sort()
    return [tech for _, _, tech in candidates[:MAX_TECHS]]


def build_summary_options(
    archetype_id: str, index: EvidenceIndex, relevance: dict[str, float]
) -> list[SummaryOption]:
    """Monta as redacoes disponiveis de um arquetipo (2 a 3 por perfil)."""
    archetype = get_archetype(archetype_id)
    if archetype is None:
        return []

    techs = _select_techs(archetype, index, relevance)
    if len(techs) < MIN_TECHS:
        return []

    options: list[SummaryOption] = []
    for variant in archetype.variants:
        # A redacao so e oferecida se todos os seus termos tiverem evidencia.
        if not all(index.has_any_evidence(term) for term in variant.required_terms):
            continue
        options.append(
            SummaryOption(
                id=variant.id,
                label=variant.label,
                archetype_id=archetype.id,
                archetype_label=archetype.label,
                text=variant.template.replace("{techs}", _join_with_and(techs)),
                techs=tuple(techs),
            )
        )
    return options


def select_summary_option(
    options: list[SummaryOption] | tuple[SummaryOption, ...],
    *,
    strategy: str,
    analysis: JobAnalysis,
) -> SummaryOption | None:
    """Escolhe, entre as redações já aprovadas do arquétipo, a mais adequada
    à estratégia (regra 9). Nunca cria texto novo — só escolhe entre as
    opções que `build_summary_options` já validou contra a evidência.

      - "balanced": primeira opção (a redação padrão do arquétipo).
      - "ats_focus": a que cobre mais termos obrigatórios/keywords de ATS
        da vaga entre as tecnologias citadas na própria redação.
      - "experience_focus": a redação mais "concreta" do arquétipo (quando
        há mais de uma, é sempre a segunda — a variante com ênfase em
        entrega/infra/ponta-a-ponta, ver `archetypes.py`).
    """
    options = list(options)
    if not options:
        return None
    if strategy == "ats_focus":
        keyword_pool = set(analysis.required_skills) | set(analysis.ats_keywords)

        def coverage(option: SummaryOption) -> tuple[int, int]:
            return (len(set(option.techs) & keyword_pool), len(option.techs))

        return max(options, key=coverage)
    if strategy == "experience_focus":
        return options[-1] if len(options) > 1 else options[0]
    return options[0]


@dataclass(frozen=True)
class AdaptationRecommendation:
    """Diagnostico: o curriculo base ja serve para esta vaga?"""

    recommended: bool
    detected_archetype: str | None
    archetype_label: str | None
    reasons: tuple[str, ...]
    ranking: tuple[ArchetypeScore, ...]


def recommend_adaptation(
    *,
    base: Resume,
    analysis: JobAnalysis,
    match: MatchReport,
    index: EvidenceIndex,
) -> AdaptationRecommendation:
    """Decide se vale sugerir a criacao de uma versao adaptada.

    O botao fica sempre disponivel; isto define apenas o selo "recomendado".
    """
    ranking = score_archetypes(analysis, match, index)
    top = ranking[0] if ranking else None
    if top is None or top.score == 0:
        return AdaptationRecommendation(False, None, None, (), tuple(ranking))

    reasons: list[str] = []
    summary_lower = base.summary.lower()

    # 1. Keyword exigida, com evidencia real, ausente do resumo do curriculo base.
    buried = [
        term
        for term in analysis.required_skills
        if index.has_any_evidence(term) and term.lower() not in summary_lower
    ]
    if buried:
        reasons.append(
            "Você tem experiência em "
            + ", ".join(buried[:4])
            + ", mas isso não aparece no resumo profissional do currículo base."
        )

    # 2. A categoria de habilidades do arquetipo nao esta entre as primeiras.
    archetype = get_archetype(top.archetype_id)
    if archetype is not None:
        pool = set(archetype.tech_pool)
        for position, category in enumerate(base.skill_categories):
            if pool & set(category.items) and position >= 2:
                reasons.append(
                    f'As tecnologias que a vaga pede estão na categoria "{category.label}", '
                    f"em {position + 1}º lugar na lista de habilidades."
                )
                break

    # 3. O perfil da vaga difere do perfil que o resumo base enfatiza.
    if top.archetype_id not in ("fullstack",) and top.score >= 4:
        reasons.append(
            f"A vaga tem perfil {top.label}, enquanto o currículo base se apresenta "
            "de forma generalista."
        )

    return AdaptationRecommendation(
        recommended=bool(reasons),
        detected_archetype=top.archetype_id,
        archetype_label=top.label,
        reasons=tuple(reasons),
        ranking=tuple(ranking),
    )
