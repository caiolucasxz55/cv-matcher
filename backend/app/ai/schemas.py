"""Contratos de saida da IA + JSON Schemas usados em `output_config.format`."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.job.models import Seniority


class JobAnalysisAiOutput(BaseModel):
    job_title: str = ""
    seniority: Seniority = "nao_identificada"
    required_terms: list[str] = Field(default_factory=list)
    preferred_terms: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    extra_keywords: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AdaptationAiOutput(BaseModel):
    prioritize_terms: list[str] = Field(default_factory=list)
    deprioritize_terms: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class AiIssue(BaseModel):
    value: str
    location: str = ""
    reason: str = ""


class ValidationAiOutput(BaseModel):
    hallucinations: list[AiIssue] = Field(default_factory=list)
    unsupported_claims: list[AiIssue] = Field(default_factory=list)
    missing_relevant_keywords: list[str] = Field(default_factory=list)
    overused_keywords: list[str] = Field(default_factory=list)
    factual_consistency: bool = True
    job_alignment: int = 0
    recommendations: list[str] = Field(default_factory=list)


_STRING_ARRAY = {"type": "array", "items": {"type": "string"}}

JOB_ANALYSIS_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "job_title": {"type": "string"},
        "seniority": {
            "type": "string",
            "enum": [
                "estagio",
                "junior",
                "pleno",
                "senior",
                "especialista",
                "lead",
                "nao_identificada",
            ],
        },
        "required_terms": _STRING_ARRAY,
        "preferred_terms": _STRING_ARRAY,
        "responsibilities": _STRING_ARRAY,
        "extra_keywords": _STRING_ARRAY,
        "notes": _STRING_ARRAY,
    },
    "required": [
        "job_title",
        "seniority",
        "required_terms",
        "preferred_terms",
        "responsibilities",
        "extra_keywords",
        "notes",
    ],
    "additionalProperties": False,
}

ADAPTATION_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "prioritize_terms": _STRING_ARRAY,
        "deprioritize_terms": _STRING_ARRAY,
        "rationale": _STRING_ARRAY,
    },
    "required": ["prioritize_terms", "deprioritize_terms", "rationale"],
    "additionalProperties": False,
}

_ISSUE_SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": "string"},
        "location": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["value", "location", "reason"],
    "additionalProperties": False,
}

VALIDATION_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "hallucinations": {"type": "array", "items": _ISSUE_SCHEMA},
        "unsupported_claims": {"type": "array", "items": _ISSUE_SCHEMA},
        "missing_relevant_keywords": _STRING_ARRAY,
        "overused_keywords": _STRING_ARRAY,
        "factual_consistency": {"type": "boolean"},
        "job_alignment": {"type": "integer"},
        "recommendations": _STRING_ARRAY,
    },
    "required": [
        "hallucinations",
        "unsupported_claims",
        "missing_relevant_keywords",
        "overused_keywords",
        "factual_consistency",
        "job_alignment",
        "recommendations",
    ],
    "additionalProperties": False,
}
