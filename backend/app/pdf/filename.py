from __future__ import annotations

import re

from app.job.taxonomy import normalize_term


def _slug(value: str) -> str:
    """Slug curto e minusculo: sem acento, sem simbolo, palavras unidas por hifen."""
    normalized = re.sub(r"[^a-z0-9]+", "-", normalize_term(value)).strip("-")
    return normalized


def build_pdf_filename(*, company: str | None = None, job_title: str | None = None) -> str:
    """Convencao de nomes curta (regra 15).

    curriculo-caio-[empresa].pdf
    curriculo-caio.pdf                 (sem empresa)

    Nunca inclui cargo, score, versao ou timestamp. `job_title` e aceito
    apenas por compatibilidade de assinatura com quem ainda o passa, mas e
    ignorado deliberadamente.
    """
    del job_title  # nunca entra no nome do arquivo (regra 15)
    company_slug = _slug(company or "")
    if company_slug:
        return f"curriculo-caio-{company_slug}.pdf"
    return "curriculo-caio.pdf"
