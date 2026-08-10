"""Implementacao do AIProvider sobre o Gemini (Google GenAI SDK).

`response_schema` recebe diretamente os modelos Pydantic de saida — o SDK
deriva o schema e ja devolve `response.parsed` validado. Ainda assim, cada
metodo revalida com Pydantic antes de devolver, mesma postura do
`AnthropicProvider`: a IA nunca entrega dado nao verificado ao resto do
sistema.

Cache exato em processo (`app.ai.cache.AsyncLRUCache`) evita repetir uma
chamada IDENTICA — mesmo racional do `AnthropicProvider`. O Gemini tambem
tem uma API de cache de contexto do lado do servidor (`CachedContent`), mas
ela exige um minimo de dezenas de milhares de tokens para compensar o custo
de manter o cache — muito acima do tamanho de um curriculo de uma pagina —
entao nao se aplica aqui; o cache exato em processo e que faz diferenca real.
"""

from __future__ import annotations

from typing import Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.ai.cache import AsyncLRUCache
from app.ai.prompts.job_analysis import (
    JOB_ANALYSIS_SYSTEM_PROMPT,
    build_job_analysis_user_prompt,
)
from app.ai.prompts.resume_adaptation import (
    RESUME_ADAPTATION_SYSTEM_PROMPT,
    build_resume_adaptation_user_prompt,
)
from app.ai.prompts.resume_validation import (
    RESUME_VALIDATION_SYSTEM_PROMPT,
    build_resume_validation_user_prompt,
)
from app.ai.provider import (
    AdaptationRequest,
    AIProvider,
    JobAnalysisRequest,
    ValidationRequest,
)
from app.ai.schemas import AdaptationAiOutput, JobAnalysisAiOutput, ValidationAiOutput

TModel = TypeVar("TModel", bound=BaseModel)


class GeminiProvider(AIProvider):
    name = "gemini"
    is_remote = True

    def __init__(self, *, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._job_analysis_cache: AsyncLRUCache[JobAnalysisAiOutput] = AsyncLRUCache()
        self._adaptation_cache: AsyncLRUCache[AdaptationAiOutput] = AsyncLRUCache()
        self._validation_cache: AsyncLRUCache[ValidationAiOutput] = AsyncLRUCache()

    async def _request_json(
        self, *, system: str, user: str, model_type: Type[TModel]
    ) -> TModel:
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=model_type,
            ),
        )

        if response.parsed is None:
            reason = ""
            if response.candidates:
                reason = f" (finish_reason={response.candidates[0].finish_reason})"
            raise RuntimeError(f"Resposta da IA sem JSON válido.{reason}")

        return model_type.model_validate(response.parsed, from_attributes=True)

    async def analyze_job_description(
        self, request: JobAnalysisRequest
    ) -> JobAnalysisAiOutput:
        async def compute() -> JobAnalysisAiOutput:
            return await self._request_json(
                system=JOB_ANALYSIS_SYSTEM_PROMPT,
                user=build_job_analysis_user_prompt(
                    description=request.description,
                    company=request.company,
                    job_title=request.job_title,
                ),
                model_type=JobAnalysisAiOutput,
            )

        return await self._job_analysis_cache.get_or_compute(request, compute)

    async def recommend_adaptation(self, request: AdaptationRequest) -> AdaptationAiOutput:
        async def compute() -> AdaptationAiOutput:
            return await self._request_json(
                system=RESUME_ADAPTATION_SYSTEM_PROMPT,
                user=build_resume_adaptation_user_prompt(
                    job_title=request.job_title,
                    company=request.company,
                    required_terms=request.required_terms,
                    preferred_terms=request.preferred_terms,
                    evidenced_terms=request.evidenced_terms,
                ),
                model_type=AdaptationAiOutput,
            )

        return await self._adaptation_cache.get_or_compute(request, compute)

    async def validate_resume(self, request: ValidationRequest) -> ValidationAiOutput:
        async def compute() -> ValidationAiOutput:
            return await self._request_json(
                system=RESUME_VALIDATION_SYSTEM_PROMPT,
                user=build_resume_validation_user_prompt(
                    base_resume_text=request.base_resume_text,
                    job_analysis_text=request.job_analysis_text,
                    adapted_resume_text=request.adapted_resume_text,
                ),
                model_type=ValidationAiOutput,
            )

        return await self._validation_cache.get_or_compute(request, compute)
