from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.pdf.filename import build_pdf_filename
from app.pdf.renderer import render_resume_pdf
from app.resume.models import Resume
from app.resume.skills_store import get_base_evidence_index
from app.validation.factual_guard import run_factual_guard

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pdf"])


class PdfRequest(BaseModel):
    resume: Resume
    company: str | None = Field(default=None, max_length=160)
    job_title: str | None = Field(default=None, max_length=160)


@router.post(
    "/pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def generate_pdf(request: PdfRequest) -> Response:
    """Gera o PDF do currículo adaptado.

    Reexecuta a checagem factual no servidor por auditoria: informação sem
    respaldo no currículo base é registrada em log, mas não bloqueia a
    geração — quem decide se segue em frente é sempre a pessoa, nunca o
    sistema.
    """
    guard = run_factual_guard(request.resume, get_base_evidence_index())
    if not guard.ok:
        logger.warning(
            "PDF gerado com informação sem respaldo no currículo base: %s",
            [finding.value for finding in (*guard.hallucinations, *guard.unsupported_claims)],
        )

    filename = build_pdf_filename(company=request.company)

    try:
        pdf = render_resume_pdf(request.resume, filename)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao renderizar o PDF")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao gerar o PDF.",
        ) from None

    return Response(
        content=pdf.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"; '
                f"filename*=UTF-8''{quote(filename)}"
            ),
            "Content-Length": str(pdf.byte_length),
            "Cache-Control": "no-store",
        },
    )
