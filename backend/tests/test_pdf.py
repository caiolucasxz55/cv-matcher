"""6. Geração do PDF (texto real, selecionável, sem metadados internos)."""

from __future__ import annotations

import base64
import re
import zlib

import pytest

from app.ai.heuristic_provider import HeuristicProvider
from app.job.models import JobInput
from app.pdf.renderer import render_resume_pdf
from app.pipeline import run_version_pipeline
from app.resume.adapt import reset_version_counter
from app.resume.base_resume import BASE_RESUME
from tests.fixtures import BACKEND_PYTHON_JOB

provider = HeuristicProvider()


@pytest.fixture(autouse=True)
def _reset_counter():
    reset_version_counter()
    yield


def decode_content_streams(pdf: bytes) -> str:
    """Descomprime os streams do PDF para inspecionar os operadores de texto.

    O ReportLab aplica `/ASCII85Decode` seguido de `/FlateDecode`, então o
    decodificador desfaz os dois na ordem inversa.
    """
    chunks: list[str] = []
    for match in re.finditer(rb"stream\r?\n", pdf):
        start = match.end()
        end = pdf.find(b"endstream", start)
        if end == -1:
            continue

        raw = pdf[start:end].strip(b"\r\n")
        for decode in (_a85_then_flate, _flate_only, _identity):
            decoded = decode(raw)
            if decoded is not None:
                chunks.append(decoded)
                break
    return "\n".join(chunks)


def _a85_then_flate(raw: bytes) -> str | None:
    try:
        return zlib.decompress(base64.a85decode(raw, adobe=True)).decode("latin-1")
    except (ValueError, zlib.error):
        return None


def _flate_only(raw: bytes) -> str | None:
    try:
        return zlib.decompress(raw).decode("latin-1")
    except zlib.error:
        return None


def _identity(raw: bytes) -> str:
    return raw.decode("latin-1", errors="replace")


def test_gera_pdf_valido():
    pdf = render_resume_pdf(BASE_RESUME, "teste.pdf")

    assert pdf.content[:5] == b"%PDF-"
    assert pdf.content.rstrip().endswith(b"%%EOF")
    assert pdf.byte_length > 3_000
    assert pdf.filename == "teste.pdf"


def test_pdf_contem_texto_real_e_selecionavel():
    pdf = render_resume_pdf(BASE_RESUME, "teste.pdf")
    content = decode_content_streams(pdf.content)

    # BT/ET delimitam blocos de texto; Tj/TJ desenham glifos.
    assert "BT" in content and "ET" in content
    assert re.search(r"T[jJ]", content)

    # Nome do candidato presente como texto, não como imagem.
    assert "Caio" in content
    # Nenhum XObject de imagem no documento.
    assert b"/Subtype /Image" not in pdf.content


def test_registra_links_como_anotacoes_clicaveis():
    pdf = render_resume_pdf(BASE_RESUME, "teste.pdf")
    assert b"/Annots" in pdf.content
    assert b"/URI" in pdf.content


def test_usa_apenas_fontes_padrao_ats_friendly():
    pdf = render_resume_pdf(BASE_RESUME, "teste.pdf")
    assert b"/Helvetica" in pdf.content
    # Fontes embutidas/subsetadas quebram alguns parsers ATS.
    assert b"/FontFile" not in pdf.content


@pytest.mark.anyio
async def test_gera_pdf_do_curriculo_adaptado_ponta_a_ponta():
    result = await run_version_pipeline(
        JobInput(
            description=BACKEND_PYTHON_JOB, company="Nubank", job_title="Backend Python"
        ),
        provider=provider,
    )
    assert result.balanced.validation.is_valid is True

    pdf = render_resume_pdf(result.balanced.adaptation.resume, result.pdf_filename)
    assert pdf.content[:5] == b"%PDF-"
    assert pdf.filename == "curriculo-caio-nubank.pdf"


@pytest.mark.anyio
async def test_pdf_nao_expoe_scores_nem_metadados_da_ia():
    result = await run_version_pipeline(
        JobInput(description=BACKEND_PYTHON_JOB), provider=provider
    )
    content = decode_content_streams(
        render_resume_pdf(result.balanced.adaptation.resume, "x.pdf").content
    )

    for forbidden in ("ATS", "Job Match", "job_match_score", "hallucination", "is_valid"):
        assert forbidden not in content
