from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

Seniority = Literal[
    "estagio", "junior", "pleno", "senior", "especialista", "lead", "nao_identificada"
]
RequirementKind = Literal["required", "preferred"]
MatchLevel = Literal["STRONG", "MEDIUM", "WEAK", "NONE"]


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class JobInput(Frozen):
    description: str
    company: str | None = None
    job_title: str | None = None


class JobRequirement(Frozen):
    term: str
    category: str
    kind: RequirementKind
    #: Trecho da vaga que originou o requisito (rastreabilidade).
    evidence: str = ""


class JobAnalysis(Frozen):
    job_title: str
    company: str
    seniority: Seniority

    keywords: tuple[str, ...] = ()
    technologies: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    programming_languages: tuple[str, ...] = ()
    databases: tuple[str, ...] = ()
    cloud: tuple[str, ...] = ()
    devops: tuple[str, ...] = ()
    ai_ml: tuple[str, ...] = ()

    required_skills: tuple[str, ...] = ()
    preferred_skills: tuple[str, ...] = ()
    requirements: tuple[JobRequirement, ...] = ()

    responsibilities: tuple[str, ...] = ()
    ats_keywords: tuple[str, ...] = ()

    candidate_matches: tuple[str, ...] = ()
    missing_requirements: tuple[str, ...] = ()

    source: str = "deterministic"
    ai_notes: tuple[str, ...] = ()


class TermMatch(Frozen):
    term: str
    category: str
    level: MatchLevel
    kind: str  # RequirementKind | "mentioned"
    #: Onde no curriculo base a evidencia foi encontrada. Vazio quando NONE.
    evidence: tuple[str, ...] = ()
    #: Termo relacionado que sustenta um match FRACO.
    related_via: str | None = None


class MatchReport(Frozen):
    matches: tuple[TermMatch, ...] = ()
    strong: tuple[TermMatch, ...] = ()
    medium: tuple[TermMatch, ...] = ()
    weak: tuple[TermMatch, ...] = ()
    missing: tuple[TermMatch, ...] = ()
    job_match_score: int = 0
    #: Peso de relevancia por termo canonico do curriculo (0..1).
    relevance: dict[str, float] = {}
