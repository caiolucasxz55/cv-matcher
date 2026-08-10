"""CAMADA ANTI-ALUCINACAO (deterministica).

Compara o curriculo adaptado com o indice de evidencias do curriculo base:
 1. Toda tecnologia detectada no adaptado precisa existir no base.
 2. Todo token textual precisa existir no vocabulario do base.
 3. Todo numero/metrica precisa existir no base.

Qualquer violacao bloqueia a geracao do PDF.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.job.taxonomy import detect_terms, normalize_term
from app.resume.evidence import EvidenceIndex
from app.resume.models import Resume

_WORD_SPLIT = re.compile(r"[^a-z0-9+#./-]+")


@dataclass(frozen=True)
class GuardFinding:
    type: str  # "hallucination" | "unsupported_claim"
    value: str
    location: str
    reason: str


@dataclass(frozen=True)
class GuardResult:
    hallucinations: tuple[GuardFinding, ...]
    unsupported_claims: tuple[GuardFinding, ...]

    @property
    def ok(self) -> bool:
        return not self.hallucinations and not self.unsupported_claims


def _tokenize(text: str) -> list[str]:
    tokens = []
    for raw in _WORD_SPLIT.split(normalize_term(text)):
        token = raw.strip("-./")
        if token:
            tokens.append(token)
    return tokens


def _collect_sections(resume: Resume) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = [("Resumo profissional", resume.summary)]

    for experience in resume.experience:
        sections.append(
            (
                f"Experiência · {experience.role} @ {experience.company}",
                f"{experience.role} {experience.company} {experience.location} {experience.period}",
            )
        )
        for bullet in experience.bullets:
            sections.append((f"Experiência · {experience.company} · bullet", bullet.text))

    for project in resume.projects:
        sections.append(
            (f"Projeto · {project.name}", f"{project.name} {project.description}")
        )
        for bullet in project.bullets:
            sections.append((f"Projeto · {project.name} · bullet", bullet.text))

    for category in resume.skill_categories:
        for item in category.items:
            sections.append((f"Habilidades · {category.label}", item))

    for education in resume.education:
        sections.append(
            ("Formação", f"{education.degree} {education.institution} {education.period}")
        )

    for course in resume.courses:
        sections.append(("Cursos", course.name))

    for language in resume.languages:
        sections.append(("Idiomas", f"{language.name} {language.level}"))

    basics = resume.basics
    sections.append(
        (
            "Dados pessoais",
            f"{basics.name} {basics.headline} {basics.location} {basics.email} {basics.phone}",
        )
    )
    return sections


def run_factual_guard(adapted: Resume, index: EvidenceIndex) -> GuardResult:
    hallucinations: list[GuardFinding] = []
    unsupported: list[GuardFinding] = []
    seen_terms: set[tuple[str, str]] = set()
    seen_tokens: set[str] = set()

    for label, text in _collect_sections(adapted):
        # 1. tecnologias e competencias reconhecidas
        for detected in detect_terms(text):
            if index.has_any_evidence(detected.canonical):
                continue
            key = (detected.canonical, label)
            if key in seen_terms:
                continue
            seen_terms.add(key)
            hallucinations.append(
                GuardFinding(
                    type="hallucination",
                    value=detected.canonical,
                    location=label,
                    reason=(
                        "Tecnologia/competência presente no currículo adaptado mas "
                        "ausente do currículo base."
                    ),
                )
            )

        # 2 e 3. vocabulario e numeros
        for token in _tokenize(text):
            if token in index.vocabulary or token in seen_tokens:
                continue
            seen_tokens.add(token)

            if any(char.isdigit() for char in token):
                unsupported.append(
                    GuardFinding(
                        type="unsupported_claim",
                        value=token,
                        location=label,
                        reason="Número/métrica não encontrado no currículo base.",
                    )
                )
            else:
                unsupported.append(
                    GuardFinding(
                        type="unsupported_claim",
                        value=token,
                        location=label,
                        reason="Termo não presente no vocabulário do currículo base.",
                    )
                )

    return GuardResult(tuple(hallucinations), tuple(unsupported))
