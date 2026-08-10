"""Confirmação de gaps pelo usuário (regra central do CV Matcher v2).

A vaga pedir uma tecnologia que não está no currículo base NÃO é
automaticamente um gap definitivo — o sistema pergunta; quem decide é
sempre a pessoa:

  - "yes"    -> a evidência passa a contar no matching e pode aparecer na
                versão adaptada, mas SÓ nesta análise/versão. O currículo
                base (`BASE_RESUME`) nunca é alterado por uma confirmação.
  - "no"     -> gap confirmado. Nunca entra no currículo.
  - "unsure" -> requisito não confirmado. Nunca entra no currículo, mas é
                reportado separado de um "não" explícito (rule 2).

Isso vale para tecnologias, ferramentas, metodologias, responsabilidades e
requisitos em geral — qualquer termo da taxonomia (`app.job.taxonomy`) pode
ser perguntado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.job.models import MatchReport
from app.job.taxonomy import normalize_term, resolve_canonical
from app.resume.evidence import EvidenceIndex, TermEvidence

ConfirmationAnswer = Literal["yes", "no", "unsure"]


@dataclass(frozen=True)
class SkillConfirmation:
    """Resposta da pessoa a uma pergunta sobre um termo que a vaga pede e o
    currículo base não evidencia."""

    term: str
    answer: ConfirmationAnswer
    #: Onde/como a experiência foi adquirida. Só relevante quando answer="yes".
    context: str = ""


@dataclass(frozen=True)
class GapQuestion:
    """Pergunta sobre um requisito sem evidência no currículo base.

    `answer` vem preenchido quando a pessoa já respondeu esta pergunta nesta
    sessão (permite ao frontend reexibir o estado sem perguntar de novo).
    """

    term: str
    category: str
    kind: str  # "required" | "preferred"
    answer: ConfirmationAnswer | None = None


def _confirmed_map(
    confirmations: tuple[SkillConfirmation, ...],
) -> dict[str, SkillConfirmation]:
    result: dict[str, SkillConfirmation] = {}
    for confirmation in confirmations:
        canonical = resolve_canonical(confirmation.term) or confirmation.term
        result[canonical] = confirmation
    return result


def pending_gap_questions(
    match: MatchReport, confirmations: tuple[SkillConfirmation, ...] = ()
) -> tuple[GapQuestion, ...]:
    """Requisitos sem evidência DIRETA no currículo base: nível NONE (nada) e
    WEAK (só um conceito relacionado, ex.: vaga pede Kubernetes e a pessoa só
    tem Docker no currículo). Em ambos os casos o termo em si não está
    comprovado — a mesma definição de "gap" já usada em `validate.py`
    (`*match.missing, *match.weak`). Só perguntamos sobre STRONG/MEDIUM se a
    pessoa nunca teria motivo: já há evidência direta.
    """
    answered = _confirmed_map(confirmations)
    questions: list[GapQuestion] = []
    seen: set[str] = set()
    for item in (*match.missing, *match.weak):
        if item.term in seen:
            continue
        seen.add(item.term)
        confirmation = answered.get(item.term)
        questions.append(
            GapQuestion(
                term=item.term,
                category=item.category,
                kind=item.kind if item.kind in ("required", "preferred") else "preferred",
                answer=confirmation.answer if confirmation else None,
            )
        )
    return tuple(questions)


def apply_confirmations(
    index: EvidenceIndex, confirmations: tuple[SkillConfirmation, ...]
) -> EvidenceIndex:
    """Devolve um NOVO índice com os termos confirmados como "yes" somados.

    "no" e "unsure" nunca alteram o índice: o termo continua sem evidência e
    continua sendo reportado como gap, exatamente como antes.
    """
    yes_confirmations = [c for c in confirmations if c.answer == "yes"]
    if not yes_confirmations:
        return index

    by_term = dict(index.by_term)
    vocabulary = set(index.vocabulary)

    for confirmation in yes_confirmations:
        canonical = resolve_canonical(confirmation.term) or confirmation.term
        citation = (
            f"Confirmado pelo usuário: {confirmation.context.strip()}"
            if confirmation.context.strip()
            else "Confirmado pelo usuário para esta vaga."
        )
        existing = by_term.get(canonical)
        sources = {"confirmed", *(existing.sources if existing else ())}
        citations = {citation, *(existing.citations if existing else ())}
        by_term[canonical] = TermEvidence(
            term=canonical,
            sources=tuple(sorted(sources)),
            citations=tuple(sorted(citations)),
        )
        for token in normalize_term(canonical).split(" "):
            if token:
                vocabulary.add(token)

    return EvidenceIndex(by_term=by_term, vocabulary=vocabulary, numbers=set(index.numbers))


def confirmed_terms(confirmations: tuple[SkillConfirmation, ...]) -> tuple[str, ...]:
    """Termos com resposta "yes", canonizados e sem duplicatas — usados para
    render a categoria auditável "Confirmado para esta vaga" na versão
    adaptada (nunca no currículo base)."""
    seen: dict[str, None] = {}
    for confirmation in confirmations:
        if confirmation.answer != "yes":
            continue
        canonical = resolve_canonical(confirmation.term) or confirmation.term
        seen.setdefault(canonical, None)
    return tuple(seen.keys())
