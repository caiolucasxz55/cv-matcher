"""Historico de versoes em memoria.

Deliberadamente NAO persiste descricoes de vaga nem o texto dos curriculos
(secao 21 — nao armazenar dados desnecessarios). Guarda apenas metadados.
"""

from __future__ import annotations

from pydantic import BaseModel

_history: list["VersionRecord"] = []


class VersionRecord(BaseModel):
    version_label: str
    version_number: int
    created_at: str
    company: str
    job_title: str
    job_match_score: int
    ats_score: int
    is_valid: bool
    pdf_filename: str
    #: "balanced" | "ats_focus" | "experience_focus" (regra 9).
    strategy: str = "balanced"


def record_version(record: VersionRecord) -> VersionRecord:
    _history.append(record)
    return record


def list_versions() -> list[VersionRecord]:
    return list(reversed(_history))


def clear_versions() -> None:
    _history.clear()
