"""Implementacao do AIProvider sobre a Messages API da Anthropic.

Usa structured outputs (`output_config.format`) para garantir JSON valido, e
revalida a resposta com Pydantic antes de devolver — a IA nunca entrega dado
nao verificado ao restante do sistema.

Duas camadas de cache reduzem quanto currículo a IA precisa reprocessar a
cada análise (ver `app.ai.cache` para o racional completo):

1. **Cache exato em processo** (`AsyncLRUCache`): pedidos IDÊNTICOS (mesmo
   currículo base + mesma vaga + mesmo currículo adaptado) reaproveitam a
   resposta anterior sem chamar a API de novo.
2. **Prompt caching nativo da Anthropic** (`cache_control`): o bloco (A) do
   prompt de validação — o currículo base, que é IDÊNTICO nas 3 variantes de
   uma mesma vaga (regra 9) mesmo quando o currículo adaptado difere — é
   marcado como reaproveitável do lado do servidor da Anthropic. Isso ajuda
   justamente no caso que o cache exato não cobre: 3 chamadas com o mesmo
   (A) mas (C) diferente continuam sendo 3 chamadas, mas a Anthropic não
   precisa reprocessar (A) do zero em cada uma.
"""

from __future__ import annotations

import json
from typing import Any, Type, TypeVar

from anthropic import AsyncAnthropic
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
    build_resume_validation_base_block,
    build_resume_validation_variable_block,
)
from app.ai.provider import (
    AdaptationRequest,
    AIProvider,
    JobAnalysisRequest,
    ValidationRequest,
)
from app.ai.schemas import (
    ADAPTATION_JSON_SCHEMA,
    AdaptationAiOutput,
    JOB_ANALYSIS_JSON_SCHEMA,
    JobAnalysisAiOutput,
    VALIDATION_JSON_SCHEMA,
    ValidationAiOutput,
)

MAX_TOKENS = 16_000

TModel = TypeVar("TModel", bound=BaseModel)

_EPHEMERAL_CACHE = {"type": "ephemeral"}


class AnthropicProvider(AIProvider):
    name = "anthropic"
    is_remote = True

    def __init__(self, *, api_key: str, model: str = "claude-opus-5") -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._job_analysis_cache: AsyncLRUCache[JobAnalysisAiOutput] = AsyncLRUCache()
        self._adaptation_cache: AsyncLRUCache[AdaptationAiOutput] = AsyncLRUCache()
        self._validation_cache: AsyncLRUCache[ValidationAiOutput] = AsyncLRUCache()

    async def _request_json(
        self,
        *,
        system: str | list[dict[str, Any]],
        messages: list[dict[str, Any]],
        json_schema: dict[str, Any],
        model_type: Type[TModel],
    ) -> TModel:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=messages,
            # `output_config` ainda nao esta tipado no SDK 0.68, mas e aceito
            # pela Messages API — o corpo e enviado como fornecido. O mesmo
            # vale para `cache_control` dentro dos blocos de `messages`.
            extra_body={
                "output_config": {
                    "format": {"type": "json_schema", "schema": json_schema}
                }
            },
        )

        if response.stop_reason == "refusal":
            raise RuntimeError("A IA recusou a requisição por política de segurança.")

        text = next(
            (block.text for block in response.content if getattr(block, "type", None) == "text"),
            None,
        )
        if text is None:
            raise RuntimeError("Resposta da IA sem bloco de texto.")

        return model_type.model_validate(json.loads(text))

    async def analyze_job_description(
        self, request: JobAnalysisRequest
    ) -> JobAnalysisAiOutput:
        async def compute() -> JobAnalysisAiOutput:
            user = build_job_analysis_user_prompt(
                description=request.description,
                company=request.company,
                job_title=request.job_title,
            )
            return await self._request_json(
                system=JOB_ANALYSIS_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user}],
                json_schema=JOB_ANALYSIS_JSON_SCHEMA,
                model_type=JobAnalysisAiOutput,
            )

        return await self._job_analysis_cache.get_or_compute(request, compute)

    async def recommend_adaptation(self, request: AdaptationRequest) -> AdaptationAiOutput:
        async def compute() -> AdaptationAiOutput:
            user = build_resume_adaptation_user_prompt(
                job_title=request.job_title,
                company=request.company,
                required_terms=request.required_terms,
                preferred_terms=request.preferred_terms,
                evidenced_terms=request.evidenced_terms,
            )
            return await self._request_json(
                system=RESUME_ADAPTATION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user}],
                json_schema=ADAPTATION_JSON_SCHEMA,
                model_type=AdaptationAiOutput,
            )

        return await self._adaptation_cache.get_or_compute(request, compute)

    async def validate_resume(self, request: ValidationRequest) -> ValidationAiOutput:
        async def compute() -> ValidationAiOutput:
            base_block = build_resume_validation_base_block(
                base_resume_text=request.base_resume_text
            )
            variable_block = build_resume_validation_variable_block(
                job_analysis_text=request.job_analysis_text,
                adapted_resume_text=request.adapted_resume_text,
            )
            return await self._request_json(
                # Prompt tambem cacheado do lado do servidor: e o mesmo texto
                # em toda chamada de validate_resume, qualquer vaga, qualquer
                # variante.
                system=[
                    {
                        "type": "text",
                        "text": RESUME_VALIDATION_SYSTEM_PROMPT,
                        "cache_control": _EPHEMERAL_CACHE,
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            # (A) e identico nas 3 variantes desta vaga (regra
                            # 9): marcado para a Anthropic reaproveitar o
                            # processamento em vez de reler o curriculo base
                            # inteiro em cada uma das 3 chamadas.
                            {
                                "type": "text",
                                "text": base_block,
                                "cache_control": _EPHEMERAL_CACHE,
                            },
                            {"type": "text", "text": variable_block},
                        ],
                    }
                ],
                json_schema=VALIDATION_JSON_SCHEMA,
                model_type=ValidationAiOutput,
            )

        return await self._validation_cache.get_or_compute(request, compute)
