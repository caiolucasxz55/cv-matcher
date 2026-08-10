# Boas práticas de Professional Summary por perfil (pesquisa, ago/2026)

Notas internas — não é texto copiado de terceiros, é uma síntese de práticas
recorrentes em guias de currículo (Novoresume, Enhancv, BeamJobs, NeuraCV,
ResumeAdapter, GetRezumAI) usada para justificar as regras de seleção de
resumo em `app/resume/archetypes.py` e na engine de 3 estratégias
(`app/resume/adapt.py`).

## Pontos convergentes entre as fontes

1. **Tamanho**: 2–4 frases. Currículo não é biografia — o resumo precisa ser
   lido em poucos segundos.
2. **Abertura forte**: primeira frase estabelece papel + domínio principal
   (ex.: "Desenvolvedor Full Stack com experiência em ..."). Isso já é como
   `summary_template.role` + `opening` funcionam no currículo base.
3. **Keywords da vaga primeiro**: termos que aparecem como requisito
   obrigatório na vaga devem aparecer o quanto antes no resumo — não só na
   seção de habilidades. É a base da estratégia **B — ATS / Keyword Focus**.
4. **Especificidade por stack**: nomear frameworks/ferramentas específicas
   (não só "backend" genérico) pesa mais que termos vagos. Para perfis de
   IA, os guias citam nominalmente RAG, LLMs, MLOps, vector DBs — o
   arquétipo `ai_ml` já usa exatamente esses termos.
5. **Impacto, não apenas atividade**: guias de 2026 recomendam evidenciar
   *resultado* (o que mudou) e não só a lista de tarefas. Como o sistema
   nunca pode inventar números, a forma honesta de aplicar isso é
   **priorizar, na reordenação, os bullets que já descrevem um resultado
   real** (ex.: "reduzindo... custo de tokens", "aumentando a segurança...").
   É a base da estratégia **C — Experience / Impact Focus**.
6. **Sem keyword stuffing**: começar a atropelar o texto com palavras-chave
   prejudica tanto ATS modernos quanto a leitura humana — já coberto pelo
   check `no-stuffing` em `validation/ats.py`.
7. **Layout ATS-safe**: coluna única, sem ícones/tabelas — já é como o PDF é
   gerado (`pdf/renderer.py`).

## Como isso vira regra de código (sem inventar nada)

| Prática | Onde entra no CV Matcher |
| --- | --- |
| Keywords obrigatórias cedo no texto | Estratégia **ats_focus**: escolhe a redação de resumo com maior sobreposição entre `techs` e `required_skills`/`ats_keywords`, e pondera reordenação por match exato com requisito obrigatório. |
| Impacto real em vez de atividade genérica | Estratégia **experience_focus**: pondera bullets por evidência profissional + riqueza de termos comprovados, e prefere a variante de resumo mais "concreta" do arquétipo (ex.: "Com ênfase em entrega", "Ponta a ponta"), que já existe no texto autoral. |
| Equilíbrio sem forçar nada | Estratégia **balanced**: comportamento padrão (a mesma lógica que já existia como modo "adaptado"), sem boost artificial. |
| Especificidade de stack por perfil | Já resolvido pelos arquétipos (`frontend`, `backend`, `fullstack`, `devops`, `ai_ml`) — cobre Full Stack, Backend, Frontend, Python (via `backend`) e AI Engineer (via `ai_ml`); DevOps/Cloud tem arquétipo dedicado. |

Nenhuma prática acima é aplicada adicionando texto novo: todas mexem em
**quais fragmentos existentes entram e em que ordem** — o vocabulário
continua limitado ao que o `EvidenceIndex` já sustenta.
