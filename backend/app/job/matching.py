"""Sistema de match entre requisitos da vaga e evidencias do curriculo base."""

from __future__ import annotations

from typing import Iterable

from app.job.models import JobAnalysis, MatchLevel, MatchReport, TermMatch
from app.job.taxonomy import get_category, get_related
from app.resume.evidence import EvidenceIndex

_LEVEL_WEIGHT: dict[MatchLevel, float] = {
    "STRONG": 1.0,
    "MEDIUM": 0.75,
    "WEAK": 0.25,
    "NONE": 0.0,
}

_KIND_WEIGHT: dict[str, float] = {"required": 3.0, "preferred": 1.0, "mentioned": 0.5}


def classify_term(index: EvidenceIndex, term: str) -> TermMatch:
    """Classifica um termo da vaga contra o indice de evidencias.

    STRONG  - tecnologia com experiencia profissional comprovada
    MEDIUM  - consta em habilidades/projetos/cursos, sem experiencia explicita
    WEAK    - apenas conceito relacionado; NAO pode ser afirmado no curriculo
    NONE    - inexistente no curriculo base => vira GAP
    """
    category = get_category(term)

    if index.has_professional_evidence(term):
        evidence = index.by_term[term].citations
        return TermMatch(
            term=term, category=category, level="STRONG", kind="mentioned", evidence=evidence
        )

    if index.has_any_evidence(term):
        evidence = index.by_term[term].citations
        return TermMatch(
            term=term, category=category, level="MEDIUM", kind="mentioned", evidence=evidence
        )

    for related in get_related(term):
        if index.has_any_evidence(related):
            return TermMatch(
                term=term,
                category=category,
                level="WEAK",
                kind="mentioned",
                evidence=(),
                related_via=related,
            )

    return TermMatch(term=term, category=category, level="NONE", kind="mentioned", evidence=())


def build_match_report(analysis: JobAnalysis, index: EvidenceIndex) -> MatchReport:
    matches: list[TermMatch] = []
    for requirement in analysis.requirements:
        classified = classify_term(index, requirement.term)
        matches.append(classified.model_copy(update={"kind": requirement.kind}))

    seen = {match.term for match in matches}
    for keyword in analysis.keywords:
        if keyword in seen:
            continue
        seen.add(keyword)
        matches.append(classify_term(index, keyword))

    earned = 0.0
    total = 0.0
    for match in matches:
        weight = _KIND_WEIGHT[match.kind]
        total += weight
        earned += weight * _LEVEL_WEIGHT[match.level]
    job_match_score = 0 if total == 0 else round((earned / total) * 100)

    # Relevancia por termo: quanto a vaga valoriza aquele termo do curriculo.
    relevance: dict[str, float] = {}
    for match in matches:
        if match.level in ("NONE", "WEAK"):
            continue
        kind_factor = (
            1.0 if match.kind == "required" else 0.7 if match.kind == "preferred" else 0.4
        )
        relevance[match.term] = max(relevance.get(match.term, 0.0), kind_factor)

    def by_level(level: MatchLevel) -> tuple[TermMatch, ...]:
        selected = [match for match in matches if match.level == level]
        selected.sort(key=lambda m: (-_KIND_WEIGHT[m.kind], m.term))
        return tuple(selected)

    return MatchReport(
        matches=tuple(matches),
        strong=by_level("STRONG"),
        medium=by_level("MEDIUM"),
        weak=by_level("WEAK"),
        missing=by_level("NONE"),
        job_match_score=job_match_score,
        relevance=relevance,
    )


def score_terms(terms: Iterable[str], relevance: dict[str, float]) -> float:
    """Score de relevancia de um conjunto de termos segundo os pesos da vaga."""
    return sum(relevance.get(term, 0.0) for term in terms)
