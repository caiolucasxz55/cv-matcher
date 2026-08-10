"""Serializacao em texto plano — formato consumido pelo validador de IA."""

from __future__ import annotations

from app.job.models import JobAnalysis
from app.resume.models import Resume


def resume_to_text(resume: Resume) -> str:
    lines: list[str] = [
        resume.basics.name,
        resume.basics.headline,
        " | ".join(
            part
            for part in (resume.basics.location, resume.basics.email, resume.basics.phone)
            if part
        ),
        " | ".join(link.label for link in resume.basics.links),
        "",
        "RESUMO PROFISSIONAL",
        resume.summary,
        "",
        "EXPERIÊNCIA",
    ]

    for experience in resume.experience:
        lines.append(f"{experience.role} — {experience.company} ({experience.location})")
        lines.append(experience.period)
        lines.extend(f"- {bullet.text}" for bullet in experience.bullets)
        lines.append("")

    if resume.projects:
        lines.append("PROJETOS")
        for project in resume.projects:
            lines.append(project.name)
            lines.append(project.description)
            lines.extend(f"- {bullet.text}" for bullet in project.bullets)
        lines.append("")

    lines.append("HABILIDADES TÉCNICAS")
    for category in resume.skill_categories:
        lines.append(f"{category.label}: {', '.join(category.items)}")
    lines.append("")

    lines.append("FORMAÇÃO")
    for education in resume.education:
        lines.append(f"{education.degree} — {education.institution} ({education.period})")
    lines.append("")

    lines.append("CURSOS")
    lines.extend(f"- {course.name}" for course in resume.courses)
    lines.append("")

    lines.append("IDIOMAS")
    lines.extend(f"{language.name}: {language.level}" for language in resume.languages)

    return "\n".join(lines)


def job_analysis_to_text(analysis: JobAnalysis) -> str:
    return "\n".join(
        [
            f"Cargo: {analysis.job_title}",
            f"Empresa: {analysis.company or '(não informada)'}",
            f"Senioridade: {analysis.seniority}",
            f"Requisitos obrigatórios: {', '.join(analysis.required_skills) or '(nenhum)'}",
            f"Requisitos desejáveis: {', '.join(analysis.preferred_skills) or '(nenhum)'}",
            f"Responsabilidades: {' | '.join(analysis.responsibilities) or '(nenhuma)'}",
            f"Keywords ATS: {', '.join(analysis.ats_keywords)}",
        ]
    )
