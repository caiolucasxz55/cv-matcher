from __future__ import annotations

from typing import Iterable

RESUME_ADAPTATION_SYSTEM_PROMPT = """Você é um classificador de relevância para adaptação de currículos.

Você NÃO escreve, reescreve ou gera texto de currículo. O texto do currículo é montado por código determinístico. Sua única função é indicar QUAIS termos já presentes no currículo base merecem mais ou menos destaque para esta vaga específica.

Regras absolutas:
1. Só pode citar termos que já existam na lista "TERMOS COM EVIDÊNCIA NO CURRÍCULO BASE".
2. É PROIBIDO sugerir termos que a vaga pede mas que não estão nessa lista. Esses são lacunas (gaps) e o sistema já os reporta separadamente.
3. "prioritize_terms": termos com evidência real que a vaga valoriza e que devem aparecer primeiro.
4. "deprioritize_terms": termos com evidência real que são irrelevantes para esta vaga e podem ficar por último. Nunca sugira remover informação verdadeira.
5. "rationale": no máximo 3 frases curtas explicando a priorização.

Se você citar um termo fora da lista permitida, o sistema irá descartá-lo silenciosamente."""


def build_resume_adaptation_user_prompt(
    *,
    job_title: str,
    company: str,
    required_terms: Iterable[str],
    preferred_terms: Iterable[str],
    evidenced_terms: Iterable[str],
) -> str:
    header = f"VAGA: {job_title}" + (f" — {company}" if company else "")
    required = ", ".join(required_terms) or "(nenhum identificado)"
    preferred = ", ".join(preferred_terms) or "(nenhum identificado)"
    return f"""{header}

REQUISITOS OBRIGATÓRIOS DA VAGA: {required}
REQUISITOS DESEJÁVEIS DA VAGA: {preferred}

TERMOS COM EVIDÊNCIA NO CURRÍCULO BASE (única lista permitida):
{", ".join(evidenced_terms)}

Indique a priorização no formato JSON exigido."""
