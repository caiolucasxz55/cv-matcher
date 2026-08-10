from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class AtsCheck(Frozen):
    id: str
    label: str
    passed: bool
    weight: int
    detail: str


class AtsReport(Frozen):
    score: int
    checks: tuple[AtsCheck, ...] = ()
    overused_keywords: tuple[str, ...] = ()


class ValidationIssue(Frozen):
    value: str
    location: str
    reason: str
    source: str  # "deterministic" | "ai"


class ValidationResult(Frozen):
    """Contrato do Resume Validator (secao 9 da especificacao)."""

    is_valid: bool
    score: int

    hallucinations: tuple[ValidationIssue, ...] = ()
    unsupported_claims: tuple[ValidationIssue, ...] = ()
    missing_relevant_keywords: tuple[str, ...] = ()
    overused_keywords: tuple[str, ...] = ()

    factual_consistency: bool
    ats_quality: int
    job_alignment: int

    recommendations: tuple[str, ...] = ()
    ats_checks: tuple[AtsCheck, ...] = ()
    validator: str  # "deterministic" | "deterministic+ai"
