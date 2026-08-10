"""Modelo de dados do curriculo.

Todos os modelos sao imutaveis (`frozen=True`): o curriculo base nunca e
alterado, cada adaptacao produz uma nova versao derivada.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class ResumeLink(Frozen):
    label: str
    url: str


class ResumeBasics(Frozen):
    name: str
    headline: str
    location: str
    email: str
    phone: str
    links: tuple[ResumeLink, ...] = ()


class ResumeExperienceBullet(Frozen):
    id: str
    text: str
    #: Termos canonicos evidenciados por este bullet. Fonte de verdade factual.
    terms: tuple[str, ...] = ()


class ResumeExperience(Frozen):
    id: str
    role: str
    company: str
    location: str
    period: str
    current: bool = False
    bullets: tuple[ResumeExperienceBullet, ...] = ()


class ResumeProjectBullet(Frozen):
    id: str
    text: str
    terms: tuple[str, ...] = ()


class ResumeProject(Frozen):
    id: str
    name: str
    description: str
    terms: tuple[str, ...] = ()
    bullets: tuple[ResumeProjectBullet, ...] = ()


class ResumeSkillCategory(Frozen):
    id: str
    label: str
    items: tuple[str, ...] = ()


class ResumeEducation(Frozen):
    id: str
    degree: str
    institution: str
    period: str


class ResumeCourse(Frozen):
    id: str
    name: str
    terms: tuple[str, ...] = ()


class ResumeLanguage(Frozen):
    name: str
    level: str


class SummaryFragment(Frozen):
    """Fragmento de texto aprovado, derivado do resumo do curriculo base."""

    id: str
    text: str
    terms: tuple[str, ...] = ()


class ResumeSummaryTemplate(Frozen):
    role: str
    opening: str
    capabilities: tuple[SummaryFragment, ...] = ()
    focus: tuple[SummaryFragment, ...] = ()
    fallback: str


class Resume(Frozen):
    id: str
    version: str
    kind: str  # "base" | "adapted"
    basics: ResumeBasics
    summary: str
    experience: tuple[ResumeExperience, ...] = ()
    projects: tuple[ResumeProject, ...] = ()
    skill_categories: tuple[ResumeSkillCategory, ...] = ()
    education: tuple[ResumeEducation, ...] = ()
    courses: tuple[ResumeCourse, ...] = ()
    languages: tuple[ResumeLanguage, ...] = ()
    summary_template: ResumeSummaryTemplate
