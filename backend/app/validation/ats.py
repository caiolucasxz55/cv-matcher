"""Avaliacao ATS deterministica: estrutura, contatos, densidade de keywords e
ausencia de elementos que quebram parsers (tabelas, icones, imagens).
"""

from __future__ import annotations

import re

from app.job.taxonomy import normalize_term
from app.resume.models import Resume
from app.validation.models import AtsCheck, AtsReport

MAX_KEYWORD_DENSITY = 0.035  # 3,5% do texto = sinal de keyword stuffing

_GRAPHIC_CHARS = re.compile("[←-⯿🀀-🫿️]")


def _full_text(resume: Resume) -> str:
    parts: list[str] = [resume.summary]
    for experience in resume.experience:
        parts.append(f"{experience.role} {experience.company} {experience.period}")
        parts.extend(bullet.text for bullet in experience.bullets)
    for project in resume.projects:
        parts.append(f"{project.name} {project.description}")
        parts.extend(bullet.text for bullet in project.bullets)
    parts.extend(f"{c.label}: {', '.join(c.items)}" for c in resume.skill_categories)
    parts.extend(f"{e.degree} {e.institution}" for e in resume.education)
    parts.extend(course.name for course in resume.courses)
    parts.extend(f"{lang.name} {lang.level}" for lang in resume.languages)
    return "\n".join(parts)


def evaluate_ats(resume: Resume) -> AtsReport:
    text = _full_text(resume)
    words = [word for word in normalize_term(text).split(" ") if word]
    total_words = len(words)

    counts: dict[str, int] = {}
    for word in words:
        if len(word) < 4:
            continue
        counts[word] = counts.get(word, 0) + 1

    overused = tuple(
        word
        for word, count in sorted(counts.items(), key=lambda item: -item[1])
        if total_words > 0 and count / total_words > MAX_KEYWORD_DENSITY and count >= 5
    )

    checks: tuple[AtsCheck, ...] = (
        AtsCheck(
            id="contact",
            label="Dados de contato completos",
            passed=(
                "@" in resume.basics.email
                and bool(resume.basics.phone)
                and bool(resume.basics.location)
            ),
            weight=15,
            detail="E-mail, telefone e localização presentes como texto real.",
        ),
        AtsCheck(
            id="sections",
            label="Seções padrão reconhecíveis",
            passed=bool(
                resume.summary
                and resume.experience
                and resume.skill_categories
                and resume.education
            ),
            weight=20,
            detail="Resumo, Experiência, Habilidades e Formação presentes com títulos claros.",
        ),
        AtsCheck(
            id="summary-length",
            label="Resumo com tamanho adequado",
            passed=120 <= len(resume.summary) <= 750,
            weight=10,
            detail=f"Resumo com {len(resume.summary)} caracteres (ideal: 120–750).",
        ),
        AtsCheck(
            id="bullets",
            label="Experiência descrita em bullets objetivos",
            passed=all(
                len(experience.bullets) >= 2
                and all(len(bullet.text) <= 400 for bullet in experience.bullets)
                for experience in resume.experience
            ),
            weight=15,
            detail="Cada experiência tem ao menos 2 bullets e nenhum bullet excessivamente longo.",
        ),
        AtsCheck(
            id="skills-flat",
            label="Habilidades em lista simples",
            passed=all(bool(category.items) for category in resume.skill_categories),
            weight=10,
            detail="Habilidades listadas como texto separado por vírgula, sem tabelas.",
        ),
        AtsCheck(
            id="no-graphics",
            label="Sem ícones ou gráficos substituindo palavras",
            passed=_GRAPHIC_CHARS.search(text) is None,
            weight=15,
            detail="Nenhum emoji, ícone ou símbolo gráfico usado no lugar de texto.",
        ),
        AtsCheck(
            id="no-stuffing",
            label="Sem keyword stuffing",
            passed=not overused,
            weight=15,
            detail=(
                "Densidade de palavras dentro do limite saudável."
                if not overused
                else f"Palavras repetidas em excesso: {', '.join(overused)}."
            ),
        ),
    )

    total_weight = sum(check.weight for check in checks)
    earned = sum(check.weight for check in checks if check.passed)

    return AtsReport(
        score=0 if total_weight == 0 else round((earned / total_weight) * 100),
        checks=checks,
        overused_keywords=overused,
    )
