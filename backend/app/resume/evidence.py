"""Indice de evidencias do curriculo base.

Este indice e a autoridade factual do sistema: nada pode ser afirmado no
curriculo adaptado se nao tiver uma entrada aqui.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.job.taxonomy import detect_terms, normalize_term, resolve_canonical
from app.resume.archetypes import all_archetype_texts
from app.resume.models import Resume

_WORD_SPLIT = re.compile(r"[^a-z0-9+#./-]+")

EvidenceSource = str  # "experience" | "summary" | "skills" | "project" | "course" | "language"


@dataclass(frozen=True)
class TermEvidence:
    term: str
    sources: tuple[str, ...]
    #: Trechos do curriculo base que sustentam o termo.
    citations: tuple[str, ...]


@dataclass
class EvidenceIndex:
    by_term: dict[str, TermEvidence] = field(default_factory=dict)
    #: Vocabulario textual completo do curriculo base (tokens normalizados).
    vocabulary: set[str] = field(default_factory=set)
    #: Numeros presentes no curriculo base (bloqueia metricas inventadas).
    numbers: set[str] = field(default_factory=set)

    def has_any_evidence(self, term: str) -> bool:
        return term in self.by_term

    def has_professional_evidence(self, term: str) -> bool:
        """Evidencia profissional = usado em experiencia real ou no resumo."""
        evidence = self.by_term.get(term)
        if evidence is None:
            return False
        return "experience" in evidence.sources or "summary" in evidence.sources


def _tokenize(text: str) -> list[str]:
    tokens = []
    for raw in _WORD_SPLIT.split(normalize_term(text)):
        token = raw.strip("-./")
        if token:
            tokens.append(token)
    return tokens


def build_evidence_index(resume: Resume) -> EvidenceIndex:
    index = EvidenceIndex()
    accumulator: dict[str, tuple[set[str], set[str]]] = {}

    def absorb(text: str) -> None:
        for token in _tokenize(text):
            index.vocabulary.add(token)
            if any(char.isdigit() for char in token):
                index.numbers.add(token)

    def push(term: str, source: str, citation: str) -> None:
        sources, citations = accumulator.setdefault(term, (set(), set()))
        sources.add(source)
        if citation:
            citations.add(citation[:200])

    # --- resumo profissional
    absorb(resume.summary)
    for detected in detect_terms(resume.summary):
        push(detected.canonical, "summary", resume.summary)

    # --- experiencia profissional (evidencia mais forte)
    for experience in resume.experience:
        absorb(f"{experience.role} {experience.company} {experience.location} {experience.period}")
        for bullet in experience.bullets:
            absorb(bullet.text)
            terms = set(bullet.terms)
            terms.update(item.canonical for item in detect_terms(bullet.text))
            for term in terms:
                push(term, "experience", bullet.text)

    # --- projetos
    for project in resume.projects:
        absorb(f"{project.name} {project.description}")
        terms = set(project.terms)
        terms.update(
            item.canonical for item in detect_terms(f"{project.name} {project.description}")
        )
        for term in terms:
            push(term, "project", project.description)
        for bullet in project.bullets:
            absorb(bullet.text)
            bullet_terms = set(bullet.terms)
            bullet_terms.update(item.canonical for item in detect_terms(bullet.text))
            for term in bullet_terms:
                push(term, "project", bullet.text)

    # --- habilidades declaradas
    for category in resume.skill_categories:
        absorb(category.label)
        for item in category.items:
            absorb(item)
            canonical = resolve_canonical(item) or item
            push(canonical, "skills", f"{category.label}: {item}")

    # --- cursos
    for course in resume.courses:
        absorb(course.name)
        terms = set(course.terms)
        terms.update(item.canonical for item in detect_terms(course.name))
        for term in terms:
            push(term, "course", f"Curso: {course.name}")

    # --- formacao e idiomas
    for education in resume.education:
        absorb(f"{education.degree} {education.institution} {education.period}")
    for language in resume.languages:
        absorb(f"{language.name} {language.level}")
        canonical = resolve_canonical(language.name) or language.name
        push(canonical, "language", f"{language.name}: {language.level}")

    # --- fragmentos aprovados do resumo (texto derivado do curriculo base;
    #     fazem parte do dado imutavel, nao sao gerados por IA)
    template = resume.summary_template
    absorb(f"{template.role} {template.opening} {template.fallback}")
    for fragment in (*template.capabilities, *template.focus):
        absorb(fragment.text)
        for term in fragment.terms:
            if term in accumulator:
                push(term, "summary", fragment.text)

    # --- redacoes de arquetipo (texto declarado pelo autor, nao gerado por IA;
    #     mesmo status dos fragmentos de `summary_template`)
    for text in all_archetype_texts():
        absorb(text)

    # --- dados pessoais
    basics = resume.basics
    absorb(
        f"{basics.name} {basics.headline} {basics.location} {basics.email} {basics.phone}"
    )
    for link in basics.links:
        absorb(link.label)

    index.by_term = {
        term: TermEvidence(term, tuple(sorted(sources)), tuple(sorted(citations)))
        for term, (sources, citations) in accumulator.items()
    }
    return index
