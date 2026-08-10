from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ai.factory import get_ai_provider
from app.config import get_settings
from app.routers import adapt, pdf, skills

logging.basicConfig(level=logging.INFO)

settings = get_settings()

app = FastAPI(
    title="CV Matcher API",
    description=(
        "Adapta um currículo base para vagas específicas sem inventar experiência. "
        "A adaptação é determinística; a IA atua apenas como analista e validadora."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(adapt.router, prefix="/api")
app.include_router(pdf.router, prefix="/api")
app.include_router(skills.router, prefix="/api")


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, object]:
    provider = get_ai_provider()
    payload: dict[str, object] = {
        "status": "ok",
        "ai_provider": provider.name,
        "ai_remote": provider.is_remote,
    }

    # Observabilidade do cache de IA (app.ai.cache) — só existe em providers
    # remotos (Anthropic/Gemini); o heurístico não faz chamadas externas.
    validation_cache = getattr(provider, "_validation_cache", None)
    if validation_cache is not None:
        payload["ai_cache"] = {
            "validation_entries": len(validation_cache),
            "validation_hit_rate": validation_cache.stats.hit_rate,
        }

    return payload
