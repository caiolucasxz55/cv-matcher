"""Formato Gupy — dois blocos de texto prontos para colar num ATS de campos
separados (a Gupy não aceita currículo em PDF: cada experiência vira um
título de cargo + empresa + datas + um campo de texto livre "Descrição de
atividades", e as habilidades viram tags soltas à parte).

Mesma garantia do resto do motor de adaptação (`app.resume.adapt`): nada é
reescrito ou inventado. O parágrafo de atividades é a concatenação literal
dos bullets que já existem no currículo base, apenas reordenados por
relevância — a mesma lógica de `_reorder_experience` (`score_terms`, de
`app.job.matching`). A lista de palavras-chave é apenas o achatamento das
habilidades já declaradas, reordenadas do mesmo jeito.
"""

from __future__ import annotations

from app.job.matching import score_terms
from app.job.taxonomy import detect_terms, resolve_canonical
from app.resume.models import ResumeExperience, ResumeSkillCategory


def build_activity_paragraph(
    experience: ResumeExperience, relevance: dict[str, float]
) -> str:
    """Parágrafo (não bullets) para o campo "Descrição de atividades" da
    Gupy: junta o texto LITERAL dos bullets de UMA experiência, reordenados
    por relevância para a vaga — a atividade mais aderente vem primeiro.
    Nenhuma frase é reescrita ou criada; a única variação possível é a ordem.

    Aceita uma única `ResumeExperience` por chamada (não a lista inteira do
    currículo) para já funcionar sem alteração no dia em que houver mais de
    uma experiência — quem chama decide se gera um parágrafo por vaga de
    emprego ou só para a mais recente.
    """
    scored: list[tuple[float, int, str]] = []
    for position, bullet in enumerate(experience.bullets):
        terms = set(bullet.terms)
        terms.update(item.canonical for item in detect_terms(bullet.text))
        score = score_terms(terms, relevance)
        scored.append((-score, position, bullet.text))

    scored.sort(key=lambda entry: (entry[0], entry[1]))
    return " ".join(text for _, _, text in scored)


def build_keyword_list(
    skill_categories: tuple[ResumeSkillCategory, ...], relevance: dict[str, float]
) -> list[str]:
    """Achata as habilidades já declaradas no currículo (todas as categorias)
    numa lista única, ordenada pela relevância da vaga — mais relevante
    primeiro, empates preservam a ordem de declaração original. Pronta para
    virar tags no campo de habilidades da Gupy. Nenhum termo fora do que já
    está declarado no currículo entra aqui."""
    scored: list[tuple[float, int, str]] = []
    seen: set[str] = set()
    position = 0
    for category in skill_categories:
        for item in category.items:
            if item in seen:
                position += 1
                continue
            seen.add(item)
            canonical = resolve_canonical(item) or item
            scored.append((-relevance.get(canonical, 0.0), position, item))
            position += 1

    scored.sort(key=lambda entry: (entry[0], entry[1]))
    return [item for _, _, item in scored]
