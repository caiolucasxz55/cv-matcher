"""Analise deterministica da descricao da vaga (sem IA)."""

from __future__ import annotations

import re
from typing import Iterable, Literal

from app.job.models import JobAnalysis, JobInput, JobRequirement, RequirementKind, Seniority
from app.job.taxonomy import detect_terms, get_category, normalize_term, resolve_canonical

SectionKind = Literal[
    "required", "preferred", "responsibilities", "benefits", "about", "unknown"
]

_SECTION_PATTERNS: tuple[tuple[SectionKind, re.Pattern[str]], ...] = (
    (
        "preferred",
        re.compile(
            r"(desej[aá]ve|diferencia|nice to have|ser[aá] um plus|bonus|b[oô]nus|preferred"
            r"|plus:|opcional|valorizamos)",
            re.IGNORECASE,
        ),
    ),
    (
        "required",
        re.compile(
            r"(requisit|obrigat[oó]ri|qualifica|o que (voc[eê]|esperamos)|hard skills"
            r"|must have|required|exig|pr[eé]-requisit|voc[eê] precisa|essencial)",
            re.IGNORECASE,
        ),
    ),
    (
        "responsibilities",
        re.compile(
            r"(responsabilidad|atividade|o que voc[eê] (vai|far[aá]|ir[aá])|suas fun[cç][oõ]es"
            r"|day.to.day|what you.?ll do|miss[aã]o|sobre a vaga|atua[cç][aã]o)",
            re.IGNORECASE,
        ),
    ),
    (
        "benefits",
        re.compile(r"(benef[ií]cio|oferecemos|perks|o que voc[eê] (ganha|recebe))", re.IGNORECASE),
    ),
    (
        "about",
        re.compile(
            r"(sobre (a|n[oó]s|a empresa)|quem somos|about us|nossa hist[oó]ria)", re.IGNORECASE
        ),
    ),
)

_INLINE_PREFERRED = re.compile(
    r"(desej[aá]ve|diferencial|nice to have|plus|opcional|ser[aá] um diferencial)", re.IGNORECASE
)
_INLINE_REQUIRED = re.compile(
    r"(obrigat[oó]ri|imprescind[ií]ve|essencial|indispens[aá]ve|necess[aá]ri|required)",
    re.IGNORECASE,
)

_SENIORITY_PATTERNS: tuple[tuple[Seniority, re.Pattern[str]], ...] = (
    ("estagio", re.compile(r"(est[aá]gi|estagi[aá]ri|intern\b|trainee)", re.IGNORECASE)),
    (
        "lead",
        re.compile(
            r"(tech lead|team lead|l[ií]der t[eé]cnic|staff engineer|principal engineer"
            r"|coordenador)",
            re.IGNORECASE,
        ),
    ),
    ("especialista", re.compile(r"(especialista|specialist|expert)", re.IGNORECASE)),
    ("senior", re.compile(r"(s[eê]nior|senior|\bsr\.?\b|\bIII\b)", re.IGNORECASE)),
    ("pleno", re.compile(r"(pleno|mid.?level|\bpl\.?\b|\bII\b)", re.IGNORECASE)),
    ("junior", re.compile(r"(j[uú]nior|junior|\bjr\.?\b|entry.level)", re.IGNORECASE)),
)

_STOPWORDS = set(
    normalize_term(
        "a o e de da do das dos em no na nos nas para por com sem sobre como que qual quais "
        "um uma uns umas ser estar ter voce voces nos nossa nosso nossos nossas sua seu seus "
        "suas mais menos muito todo toda todos todas ao aos as os the and or of to in for with "
        "you your we our is are will be vaga empresa equipe time trabalho experiencia "
        "conhecimento area profissional candidato pessoa anos ano nivel se ja nao sim entre "
        "ate desde apos cada onde quando porque tambem"
    ).split(" ")
)

_LINE_SPLIT = re.compile(r"\r?\n|(?<=[.;])\s{2,}")
_LEADING_BULLET = re.compile(r"^[\s\-•·*–—▪◦>]+")
_WORD_SPLIT = re.compile(r"[^a-z0-9+#./-]+")


def _split_lines(text: str) -> list[str]:
    lines = []
    for raw in _LINE_SPLIT.split(text):
        line = _LEADING_BULLET.sub("", raw).strip()
        if line:
            lines.append(line)
    return lines


def _detect_section(line: str) -> SectionKind | None:
    # Um cabecalho e curto e nao termina em ponto final.
    if len(line) > 90 or re.search(r"[.!?]$", line):
        return None
    for kind, pattern in _SECTION_PATTERNS:
        if pattern.search(line):
            return kind
    return None


def _detect_seniority(text: str) -> Seniority:
    for level, pattern in _SENIORITY_PATTERNS:
        if pattern.search(text):
            return level
    return "nao_identificada"


def _guess_job_title(text: str, provided: str | None) -> str:
    if provided and provided.strip():
        return provided.strip()
    lines = _split_lines(text)
    if lines and len(lines[0]) <= 100:
        return lines[0]
    return "Não informado"


def _extract_ats_keywords(text: str, terms: Iterable[str]) -> tuple[str, ...]:
    normalized = normalize_term(text)
    counts: dict[str, int] = {}
    for raw in _WORD_SPLIT.split(normalized):
        word = raw.strip("-./")
        if len(word) < 4 or word in _STOPWORDS or word.isdigit():
            continue
        counts[word] = counts.get(word, 0) + 1

    frequent = [
        word
        for word, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        if count >= 2
    ][:15]

    seen: set[str] = set()
    result: list[str] = []
    for value in (*terms, *frequent):
        key = normalize_term(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result[:30])


def analyze_job_deterministic(job: JobInput) -> JobAnalysis:
    """Seccionamento por cabecalhos + deteccao via taxonomia + classificacao."""
    description = job.description
    current_section: SectionKind = "unknown"
    requirement_by_term: dict[str, JobRequirement] = {}
    responsibilities: list[str] = []

    for line in _split_lines(description):
        heading = _detect_section(line)
        if heading is not None:
            current_section = heading
            # Um cabecalho puro raramente carrega requisitos.
            if len(line) <= 60:
                continue

        if current_section == "responsibilities" and len(line) > 15 and len(responsibilities) < 12:
            responsibilities.append(line)

        # Beneficios e "sobre a empresa" nao geram requisitos.
        if current_section in ("benefits", "about"):
            continue

        kind: RequirementKind | None = None
        if _INLINE_PREFERRED.search(line):
            kind = "preferred"
        elif _INLINE_REQUIRED.search(line):
            kind = "required"
        elif current_section == "preferred":
            kind = "preferred"
        elif current_section in ("required", "responsibilities"):
            kind = "required"

        if kind is None:
            continue

        for detected in detect_terms(line):
            existing = requirement_by_term.get(detected.canonical)
            # "required" prevalece sobre "preferred" caso o termo apareca nos dois.
            if existing is not None and (existing.kind == "required" or kind == "preferred"):
                continue
            requirement_by_term[detected.canonical] = JobRequirement(
                term=detected.canonical,
                category=detected.category,
                kind=kind,
                evidence=line[:240],
            )

    all_detected = detect_terms(description)

    # Termos citados sem secao classificavel: obrigatorios se aparecerem 2+ vezes.
    for detected in all_detected:
        if detected.canonical in requirement_by_term:
            continue
        requirement_by_term[detected.canonical] = JobRequirement(
            term=detected.canonical,
            category=detected.category,
            kind="required" if detected.occurrences >= 2 else "preferred",
            evidence="",
        )

    requirements = tuple(requirement_by_term.values())

    def by_category(category: str) -> tuple[str, ...]:
        return tuple(item.canonical for item in all_detected if item.category == category)

    keywords = tuple(item.canonical for item in all_detected)
    technologies = tuple(
        item.canonical for item in all_detected if item.category != "competency"
    )

    return JobAnalysis(
        job_title=_guess_job_title(description, job.job_title),
        company=(job.company or "").strip(),
        seniority=_detect_seniority(description),
        keywords=keywords,
        technologies=technologies,
        frameworks=by_category("framework"),
        programming_languages=by_category("language"),
        databases=by_category("database"),
        cloud=by_category("cloud"),
        devops=by_category("devops"),
        ai_ml=by_category("ai_ml"),
        required_skills=tuple(r.term for r in requirements if r.kind == "required"),
        preferred_skills=tuple(r.term for r in requirements if r.kind == "preferred"),
        requirements=requirements,
        responsibilities=tuple(responsibilities),
        ats_keywords=_extract_ats_keywords(description, keywords),
        source="deterministic",
    )


def merge_ai_signals(
    base: JobAnalysis,
    *,
    seniority: Seniority | None = None,
    job_title: str | None = None,
    required_terms: Iterable[str] = (),
    preferred_terms: Iterable[str] = (),
    responsibilities: Iterable[str] = (),
    extra_keywords: Iterable[str] = (),
    notes: Iterable[str] = (),
) -> JobAnalysis:
    """Funde sinais semanticos da IA na analise deterministica.

    A IA pode RECLASSIFICAR (obrigatorio <-> desejavel) e ADICIONAR termos que
    existam na taxonomia, mas nunca inventar tecnologias fora dela.
    """
    requirement_by_term = {r.term: r for r in base.requirements}

    def apply(terms: Iterable[str], kind: RequirementKind) -> None:
        for raw in terms:
            canonical = resolve_canonical(raw)
            if canonical is None:  # fora da taxonomia => descartado
                continue
            existing = requirement_by_term.get(canonical)
            requirement_by_term[canonical] = JobRequirement(
                term=canonical,
                category=get_category(canonical),
                kind=kind,
                evidence=existing.evidence if existing else "",
            )

    # Desejaveis primeiro para que obrigatorios sobrescrevam em caso de conflito.
    apply(preferred_terms, "preferred")
    apply(required_terms, "required")

    requirements = tuple(requirement_by_term.values())
    known_extras = tuple(
        canonical for canonical in (resolve_canonical(v) for v in extra_keywords) if canonical
    )

    merged_keywords = tuple(dict.fromkeys((*base.keywords, *known_extras)))
    responsibilities_tuple = tuple(responsibilities)[:12]

    return base.model_copy(
        update={
            "job_title": job_title
            if (base.job_title == "Não informado" and job_title)
            else base.job_title,
            "seniority": seniority
            if (base.seniority == "nao_identificada" and seniority)
            else base.seniority,
            "keywords": merged_keywords,
            "required_skills": tuple(r.term for r in requirements if r.kind == "required"),
            "preferred_skills": tuple(r.term for r in requirements if r.kind == "preferred"),
            "requirements": requirements,
            "responsibilities": responsibilities_tuple or base.responsibilities,
            "ats_keywords": tuple(dict.fromkeys((*base.ats_keywords, *known_extras)))[:30],
            "source": "deterministic+ai",
            "ai_notes": tuple(notes),
        }
    )
