from __future__ import annotations

RESUME_VALIDATION_SYSTEM_PROMPT = """Você é o Resume Validator: um auditor factual de currículos adaptados.

Você recebe (A) o CURRÍCULO BASE, (B) a ANÁLISE DA VAGA e (C) o CURRÍCULO ADAPTADO. Sua função é auditar (C) contra (A).

Um currículo adaptado é VÁLIDO quando todas as afirmações que ele faz têm respaldo direto no currículo base. Reordenar, reorganizar e reescrever levemente é permitido. Adicionar fato novo não é.

Reporte em "hallucinations" qualquer:
- tecnologia, ferramenta, linguagem ou framework presente em (C) mas ausente de (A);
- empresa, cargo, instituição, certificação ou formação que não exista em (A);
- projeto que não exista em (A);
- métrica, número, percentual ou tempo de experiência que não exista em (A).

Reporte em "unsupported_claims" qualquer afirmação que, embora não seja claramente inventada, vá além do que (A) sustenta — por exemplo, alegar domínio ou especialização onde (A) apenas lista a tecnologia entre habilidades.

Reporte em "missing_relevant_keywords" apenas termos que a vaga exige E que existem em (A), mas que não aparecem em (C). NUNCA liste aqui algo que a vaga pede mas que não existe em (A) — isso é uma lacuna legítima do candidato, não um erro do currículo.

"overused_keywords": termos repetidos de forma artificial em (C) (keyword stuffing).
"job_alignment": 0 a 100, o quanto (C) evidencia aderência real à vaga.
"factual_consistency": false se houver qualquer item em "hallucinations".
"recommendations": até 5 recomendações objetivas e acionáveis.

Seja rigoroso. Um falso negativo (deixar passar informação inventada) é o pior erro possível neste sistema."""


def build_resume_validation_base_block(*, base_resume_text: str) -> str:
    """Bloco (A) isolado — o currículo base é imutável, então este texto é
    IDÊNTICO em toda validação de toda variante de toda vaga. Providers que
    suportam cache de prompt (ex.: Anthropic `cache_control`) marcam este
    bloco como reaproveitável em vez de reprocessá-lo a cada chamada."""
    return f"""(A) CURRÍCULO BASE — única fonte de verdade factual:
\"\"\"
{base_resume_text}
\"\"\"

"""


def build_resume_validation_variable_block(
    *, job_analysis_text: str, adapted_resume_text: str
) -> str:
    """Parte que muda a cada variante/vaga — nunca vale a pena cachear no
    lado do provider, só no nosso cache exato (`app.ai.cache`)."""
    return f"""(B) ANÁLISE DA VAGA:
\"\"\"
{job_analysis_text}
\"\"\"

(C) CURRÍCULO ADAPTADO — auditar este contra (A):
\"\"\"
{adapted_resume_text}
\"\"\"

Produza o relatório de validação no formato JSON exigido."""


def build_resume_validation_user_prompt(
    *, base_resume_text: str, job_analysis_text: str, adapted_resume_text: str
) -> str:
    """Prompt completo, como um único texto — usado por providers sem
    suporte a cache de prompt em blocos (ex.: Gemini)."""
    return build_resume_validation_base_block(
        base_resume_text=base_resume_text
    ) + build_resume_validation_variable_block(
        job_analysis_text=job_analysis_text, adapted_resume_text=adapted_resume_text
    )
