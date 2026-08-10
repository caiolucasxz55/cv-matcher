"""Provider heuristico: implementa o contrato AIProvider sem chamadas de rede.

Serve como (1) fallback quando AI_API_KEY nao esta configurada e (2) base
deterministica dos testes automatizados. Nunca inventa nada — todas as saidas
derivam da analise deterministica.
"""

from __future__ import annotations

from app.ai.provider import (
    AdaptationRequest,
    AIProvider,
    JobAnalysisRequest,
    ValidationRequest,
)
from app.ai.schemas import (
    AdaptationAiOutput,
    AiIssue,
    JobAnalysisAiOutput,
    ValidationAiOutput,
)
from app.job.analyze import analyze_job_deterministic
from app.job.models import JobInput
from app.job.taxonomy import detect_terms, normalize_term


class HeuristicProvider(AIProvider):
    name = "heuristic"
    is_remote = False

    async def analyze_job_description(
        self, request: JobAnalysisRequest
    ) -> JobAnalysisAiOutput:
        analysis = analyze_job_deterministic(
            JobInput(
                description=request.description,
                company=request.company,
                job_title=request.job_title,
            )
        )
        return JobAnalysisAiOutput(
            job_title=analysis.job_title,
            seniority=analysis.seniority,
            required_terms=list(analysis.required_skills),
            preferred_terms=list(analysis.preferred_skills),
            responsibilities=list(analysis.responsibilities),
            extra_keywords=list(analysis.keywords),
            notes=["Análise produzida pelo provider heurístico (sem chamada de IA)."],
        )

    async def recommend_adaptation(self, request: AdaptationRequest) -> AdaptationAiOutput:
        evidenced = set(request.evidenced_terms)
        prioritize = [
            term
            for term in (*request.required_terms, *request.preferred_terms)
            if term in evidenced
        ]
        priority_set = set(prioritize)
        deprioritize = [term for term in request.evidenced_terms if term not in priority_set]

        return AdaptationAiOutput(
            prioritize_terms=list(dict.fromkeys(prioritize)),
            deprioritize_terms=deprioritize,
            rationale=["Priorização derivada diretamente do matching determinístico."],
        )

    async def validate_resume(self, request: ValidationRequest) -> ValidationAiOutput:
        base_terms = {item.canonical for item in detect_terms(request.base_resume_text)}
        adapted_terms = [item.canonical for item in detect_terms(request.adapted_resume_text)]

        hallucinations = [
            AiIssue(
                value=term,
                location="Currículo adaptado",
                reason="Termo ausente do currículo base.",
            )
            for term in adapted_terms
            if term not in base_terms
        ]

        job_terms = {item.canonical for item in detect_terms(request.job_analysis_text)}
        adapted_set = set(adapted_terms)
        missing = [term for term in job_terms if term in base_terms and term not in adapted_set]

        words = [word for word in normalize_term(request.adapted_resume_text).split(" ") if word]
        counts: dict[str, int] = {}
        for word in words:
            if len(word) >= 4:
                counts[word] = counts.get(word, 0) + 1
        overused = [
            word
            for word, count in counts.items()
            if count >= 6 and count / max(len(words), 1) > 0.035
        ]

        covered = sum(1 for term in job_terms if term in adapted_set)
        alignment = 0 if not job_terms else round((covered / len(job_terms)) * 100)

        recommendations = (
            [f"Considere evidenciar no currículo os termos já comprovados: "
             f"{', '.join(sorted(missing)[:5])}."]
            if missing
            else ["Nenhum ajuste factual necessário."]
        )

        return ValidationAiOutput(
            hallucinations=hallucinations,
            unsupported_claims=[],
            missing_relevant_keywords=sorted(missing),
            overused_keywords=overused,
            factual_consistency=not hallucinations,
            job_alignment=alignment,
            recommendations=recommendations,
        )
