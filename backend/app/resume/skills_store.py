"""Habilidades adicionadas pelo usuario ao curriculo base.

O curriculo base normalmente e imutavel (`base_resume.py`), mas a lista de
habilidades declaradas e um inventario simples que a propria pessoa deve
poder manter atualizado sem editar codigo. As adicoes ficam num arquivo JSON
a parte e sao mescladas com o curriculo base em tempo de leitura — o resto do
curriculo (bullets, resumo, projetos, experiencia) continua vindo
exclusivamente do codigo em `base_resume.py`.

Aceita qualquer texto, nao so o vocabulario controlado (`app.job.taxonomy`):
a lista fechada e util como sugestao, mas nao pode travar quem tem uma
habilidade real que o sistema ainda nao conhece. Quando o termo bate com o
vocabulario, e normalizado para a forma canonica (evita duplicatas como
"python" vs "Python") e passa a contar no matching automatico com vagas;
termos fora dele entram do jeito que a pessoa escreveu, aparecem no
curriculo, mas nao sao detectados na descricao de uma vaga — isso e
explicito na resposta via `recognized`.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from app.job.taxonomy import all_canonical_terms, normalize_term, resolve_canonical
from app.resume.base_resume import BASE_RESUME
from app.resume.evidence import EvidenceIndex, build_evidence_index
from app.resume.models import Resume

MAX_TERM_LENGTH = 80


class UnknownCategoryError(ValueError):
    pass


class InvalidTermError(ValueError):
    pass


class DuplicateTermError(ValueError):
    pass


class NotCustomTermError(ValueError):
    pass


def _store_path() -> Path:
    override = os.environ.get("CUSTOM_SKILLS_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent.parent / "data" / "custom_skills.json"


def _load_custom() -> dict[str, tuple[str, ...]]:
    path = _store_path()
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {category_id: tuple(items) for category_id, items in raw.items()}


def _save_custom(data: dict[str, tuple[str, ...]]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {category_id: list(items) for category_id, items in data.items() if items}
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


@lru_cache(maxsize=1)
def get_base_resume() -> Resume:
    """Curriculo base + habilidades adicionadas pelo usuario."""
    custom = _load_custom()
    if not custom:
        return BASE_RESUME

    categories = tuple(
        category.model_copy(update={"items": (*category.items, *custom.get(category.id, ()))})
        for category in BASE_RESUME.skill_categories
    )
    return BASE_RESUME.model_copy(update={"skill_categories": categories})


@lru_cache(maxsize=1)
def get_base_evidence_index() -> EvidenceIndex:
    return build_evidence_index(get_base_resume())


def reset_cache() -> None:
    get_base_resume.cache_clear()
    get_base_evidence_index.cache_clear()


def _all_declared_items(resume: Resume) -> set[str]:
    return {item for category in resume.skill_categories for item in category.items}


def _all_declared_items_normalized(resume: Resume) -> set[str]:
    return {normalize_term(item) for item in _all_declared_items(resume)}


def skills_overview() -> dict:
    """Categorias com marcacao do que e customizado + termos ainda disponiveis."""
    resume = get_base_resume()
    custom = _load_custom()
    categories = [
        {
            "id": category.id,
            "label": category.label,
            "items": [
                {
                    "name": item,
                    "custom": item in custom.get(category.id, ()),
                    "recognized": resolve_canonical(item) is not None,
                }
                for item in category.items
            ],
        }
        for category in resume.skill_categories
    ]
    used = _all_declared_items(resume)
    available = tuple(term for term in all_canonical_terms() if term not in used)
    return {"categories": categories, "available_terms": available}


def add_custom_skill(*, category_id: str, term: str) -> dict:
    resume = get_base_resume()
    if category_id not in {category.id for category in resume.skill_categories}:
        raise UnknownCategoryError(category_id)

    cleaned = term.strip()
    if not cleaned or len(cleaned) > MAX_TERM_LENGTH:
        raise InvalidTermError(term)

    # Se bater com o vocabulario controlado, normaliza para a forma canonica
    # (entra no matching automatico); senao, usa o texto como a pessoa digitou.
    canonical = resolve_canonical(cleaned) or cleaned

    if normalize_term(canonical) in _all_declared_items_normalized(resume):
        raise DuplicateTermError(canonical)

    custom = dict(_load_custom())
    custom[category_id] = (*custom.get(category_id, ()), canonical)
    _save_custom(custom)
    reset_cache()
    return skills_overview()


def remove_custom_skill(*, category_id: str, term: str) -> dict:
    canonical = resolve_canonical(term) or term
    custom = dict(_load_custom())
    items = custom.get(category_id, ())
    if canonical not in items:
        raise NotCustomTermError(term)

    custom[category_id] = tuple(item for item in items if item != canonical)
    _save_custom(custom)
    reset_cache()
    return skills_overview()
