"""Camada de abstracao de IA.

Permite trocar de provedor sem tocar no restante do sistema. A IA atua como
ANALISTA / CLASSIFICADOR / VALIDADOR — nunca como geradora livre do curriculo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.ai.schemas import AdaptationAiOutput, JobAnalysisAiOutput, ValidationAiOutput


@dataclass(frozen=True)
class JobAnalysisRequest:
    description: str
    company: str | None = None
    job_title: str | None = None


@dataclass(frozen=True)
class AdaptationRequest:
    job_title: str
    company: str
    required_terms: tuple[str, ...]
    preferred_terms: tuple[str, ...]
    #: Lista fechada: a IA so pode citar termos daqui.
    evidenced_terms: tuple[str, ...]


@dataclass(frozen=True)
class ValidationRequest:
    base_resume_text: str
    job_analysis_text: str
    adapted_resume_text: str


class AIProvider(ABC):
    name: str
    is_remote: bool

    @abstractmethod
    async def analyze_job_description(
        self, request: JobAnalysisRequest
    ) -> JobAnalysisAiOutput: ...

    @abstractmethod
    async def recommend_adaptation(self, request: AdaptationRequest) -> AdaptationAiOutput: ...

    @abstractmethod
    async def validate_resume(self, request: ValidationRequest) -> ValidationAiOutput: ...
