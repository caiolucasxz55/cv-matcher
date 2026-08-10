# CV Matcher

Ferramenta de otimização de currículo **baseada em evidências**: analisa a descrição de uma vaga, compara com um currículo base fixo e adapta a ênfase — **sem inventar experiência**.

> Não é um gerador de currículo. O texto do currículo é montado por código determinístico a partir do currículo base; a IA atua apenas como **analista, classificadora e validadora**.

---

## Arquitetura

```
frontend/   Next.js + TypeScript + React + Tailwind CSS   (UI)
backend/    Python + FastAPI                              (toda a lógica de domínio)
```

### Fluxo

O CV Matcher **não gera currículo o tempo todo**. A função principal é diagnóstica; a geração fica atrás de um botão — e antes dela, a pessoa confirma o que o sistema não pode assumir sozinho.

```
 VAGA -> ANALISE (POST /api/analyze) -> MATCH
                                          |
                     perguntas de gap: "a vaga pede X, voce tem?"
                     [Sim] [Nao] [Nao tenho certeza]  (POST /api/analyze de novo, com confirmations)
                                          |
                              [ Criar as 3 versoes ]  (POST /api/versions)
                                          v
        +------------+  +-----------------+  +----------------------+
        |  Balanced  |  |  ATS / Keyword  |  |  Experience / Impact |
        | (A)        |  |  Focus (B)      |  |  Focus (C)           |
        +------------+  +-----------------+  +----------------------+
                                          |
                     COMPARACAO (score/ATS por versao) -> RECOMENDACAO
                                          |
                        preview (igual ao layout do PDF) -> aprovar -> PDF
```

### Confirmação de gaps (nunca assumir, sempre perguntar)

Se a vaga pede algo que o currículo base não evidencia, o sistema **não** decide sozinho que é um gap: ele pergunta (`app/job/confirmations.py`).

- **Sim, tenho experiência** — a pessoa pode informar onde/como adquiriu; o termo passa a valer no matching **desta análise** e pode aparecer na versão adaptada, numa categoria auditável e separada: "Confirmado para esta vaga". O currículo base nunca é alterado por uma confirmação.
- **Não tenho experiência** — vira gap de verdade. Nunca entra no currículo.
- **Não tenho certeza** — fica como requisito não confirmado. Nunca entra no currículo, mas não é tratado como um "não" definitivo.

### O que muda e o que nunca muda

| Imutável | Variável conforme a vaga/estratégia |
| --- | --- |
| Links, dados pessoais | Resumo profissional |
| Texto literal de cada bullet | Ordem das habilidades |
| Projetos, formação, cursos, idiomas | Ordem dos bullets |
| Cargo do cabeçalho | Categoria extra "Confirmado para esta vaga" (só se houver confirmações) |
| **Todas** as stacks originais (nada é omitido) | |

### As 3 versões (regra 9 — sempre exatamente estas três)

| Versão | Estratégia | O que muda de fato |
| --- | --- | --- |
| **A — Balanced** | `balanced` | Comportamento padrão: reordenação por relevância, sem reforço artificial em nenhuma direção. |
| **B — ATS / Keyword Focus** | `ats_focus` | Pondera mais forte os termos que são requisito obrigatório/keyword de ATS da vaga; escolhe a redação de resumo com maior cobertura literal dessas palavras-chave. |
| **C — Experience / Impact Focus** | `experience_focus` | Pondera mais forte termos com evidência **profissional** (não só declarada); tende a escolher a redação mais concreta do arquétipo (a variante "com ênfase em entrega/infra/ponta-a-ponta"). |

Nenhuma estratégia remove ou inventa conteúdo — todas partilham o mesmo currículo base e o mesmo `EvidenceIndex`; a diferença é peso de relevância e qual redação (já aprovada) é escolhida. Cada versão carrega seu próprio `ValidationResult` (score composto, ATS, alinhamento com a vaga, gaps) — é esse número que alimenta a recomendação automática (regra 10, `_recommend_best_variant` em `app/pipeline.py`), nunca um valor forçado.

### Arquétipos

O sistema detecta o perfil da vaga e oferece redações escritas à mão para ele:

| Arquétipo | Evidência profissional no currículo base |
| --- | --- |
| Frontend | Frontend, React, Next.js, TypeScript, UI/UX, Usabilidade |
| Backend | Backend, Python, FastAPI, REST APIs, Segurança, Performance |
| Full Stack | as duas listas acima |
| DevOps / Cloud | Azure, AWS, Docker, CI/CD, Self-hosting, DevOps |
| IA / ML | RAG, LLMs, Chatbots, Machine Learning, Eye Tracking |

Não existe arquétipo de **Dados**: PostgreSQL, MySQL, MongoDB e Oracle SQL aparecem apenas como habilidade declarada, nunca num bullet de experiência — um resumo de perfil de dados prometeria o que a experiência não sustenta.

A detecção só pontua sinais que o candidato **tem**: uma vaga só de Kubernetes e Terraform não torna o perfil DevOps mais forte, porque nenhum dos dois existe no currículo base.

### Por que a geração automática nunca inventa experiência

Três barreiras independentes, específicas do fluxo automático de adaptação:

1. **Nada é redigido em tempo de execução.** As redações de arquétipo são texto do autor, declarado em `archetypes.py` — mesmo status dos fragmentos de `summary_template`. A IA não escreve currículo.
2. **O `{techs}` só aceita evidência.** As tecnologias que entram numa redação passam por `index.has_any_evidence()`; sem evidência, ficam de fora.
3. **A IA opera com vocabulário fechado.** Termos fora da taxonomia são descartados em `merge_ai_signals`; na recomendação de ênfase ela só cita termos já evidenciados.

Se a vaga pede Kubernetes e o candidato não tem, o sistema reporta
`GAP: Kubernetes não identificado no currículo base` e **não** adiciona automaticamente ao currículo.

**Edição manual é diferente.** A pessoa pode editar habilidades livremente — na tela de Habilidades (`/habilidades`, muda o currículo base) ou ao vivo numa versão específica (tela de revisão, com `POST /api/revalidate`). O **FactualGuard** determinístico continua comparando cada token do currículo com o vocabulário do base e sinalizando o que não tem respaldo, tanto nessas telas quanto em `POST /api/pdf` (via log de auditoria no servidor). Mas essa checagem **não bloqueia mais** a geração do PDF — ela avisa, e quem decide seguir em frente mesmo assim é sempre a pessoa, nunca o sistema automaticamente.

## Como rodar

### Backend (FastAPI)

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # opcional: preencha AI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Docs interativas: <http://localhost:8000/docs>

### Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.example .env.local  # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Aplicação: <http://localhost:3000>

### Docker

Sobe backend e frontend juntos, em portas alternativas (8001 e 3001) para não colidir com serviços já rodando nas portas padrão (8000/3000):

```bash
cp .env.example .env   # opcional: preencha AI_API_KEY
docker compose up --build
```

- Backend: <http://localhost:8001> (docs em `/docs`)
- Frontend: <http://localhost:3001>

Para mudar as portas expostas, edite `docker-compose.yml` (`ports:` de cada serviço) — lembrando de atualizar também `CORS_ORIGINS` do backend e o `NEXT_PUBLIC_API_URL` (build arg) do frontend para os novos valores.

### Sem chave de IA

Sem `AI_API_KEY`, o backend usa o **`HeuristicProvider`**: um provider determinístico e offline que implementa o mesmo contrato `AIProvider`. A aplicação funciona de ponta a ponta — análise, matching, adaptação, validação e PDF — apenas sem a camada semântica. `GET /api/health` informa qual provider está ativo.

---

## API

| Método | Rota | Descrição |
| --- | --- | --- |
| `GET` | `/api/health` | Status e provider de IA ativo |
| `POST` | `/api/analyze` | Avalia o currículo **base** (+ confirmações de gap) contra a vaga. Não adapta nada. Retorna `pending_gap_questions` |
| `POST` | `/api/versions` | Cria as **3** variantes: `balanced`, `ats_focus`, `experience_focus` + `best_variant` (recomendação) |
| `POST` | `/api/revalidate` | Botão "Reanalisar": recalcula **match + validação + recomendação juntos** a partir de um currículo editado — nunca só a validação isolada |
| `POST` | `/api/pdf` | Gera o PDF (audita o currículo antes; não bloqueia mais a geração) |
| `GET` | `/api/versions` | Histórico de versões (apenas metadados, em memória) |
| `GET` | `/api/base-resume/skills` | Habilidades técnicas do currículo base (originais + adicionadas pela pessoa) |
| `POST` | `/api/base-resume/skills` | Adiciona uma habilidade ao currículo base |
| `POST` | `/api/base-resume/skills/remove` | Remove uma habilidade adicionada anteriormente |

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"company":"Nubank","job_title":"Backend Python","description":"..."}'
```

---

## Camada de IA

`AIProvider` (`backend/app/ai/provider.py`) é uma interface abstrata com três operações — todas de **análise**, nenhuma de geração:

| Operação | Papel |
| --- | --- |
| `analyze_job_description` | Classifica requisitos como obrigatórios/desejáveis |
| `recommend_adaptation` | Indica quais termos **já existentes** destacar |
| `validate_resume` | Audita o currículo adaptado contra o base |

Implementações: `AnthropicProvider` (Claude, com structured outputs), `GeminiProvider` (Gemini, com `response_schema` a partir dos próprios modelos Pydantic) e `HeuristicProvider` (offline). O provider ativo é resolvido em `backend/app/ai/factory.py` a partir de `AI_API_KEY` + `AI_PROVIDER` ("anthropic", padrão, ou "gemini"; "heuristic" força o modo offline mesmo com chave configurada).

Prompts centralizados em `backend/app/ai/prompts/` — nenhum prompt espalhado pelo código.

### Cache — a IA não reprocessa o currículo inteiro a cada chamada

O currículo base é imutável, mas `POST /api/versions` valida **3 variantes** por vaga (regra 9), e auto-fix pode reavaliar a mesma variante de novo. Sem cache isso significa reenviar o currículo base inteiro à IA várias vezes por análise. Duas camadas (`backend/app/ai/cache.py`):

1. **Cache exato em processo** (`AsyncLRUCache`, em `AnthropicProvider` e `GeminiProvider`): pedidos byte-a-byte idênticos (mesmo currículo base + mesma vaga + mesmo currículo adaptado) reaproveitam a resposta anterior — sem heurística de similaridade. Chamadas concorrentes com a mesma chave também se juntam numa só (a segunda espera o resultado da primeira em vez de disparar outra chamada). Isso cobre reanálises repetidas e rodadas de auto-fix que não mudaram nada.
2. **Prompt caching nativo da Anthropic** (`cache_control: ephemeral` no bloco do currículo base, dentro de `AnthropicProvider.validate_resume`): cobre o caso que o cache exato não cobre — as 3 variantes de uma mesma vaga têm o mesmo currículo base mas currículo *adaptado* diferente, então são 3 chamadas de fato, mas a Anthropic não precisa reprocessar o bloco do currículo base do zero em cada uma.

`GET /api/health` expõe `ai_cache.validation_entries`/`validation_hit_rate` quando o provider ativo é remoto.

**Trade-off de privacidade:** o cache vive só em memória do processo, é limitado por tamanho (LRU, descarta o mais antigo) e é descartado ao reiniciar o servidor — nunca é gravado em disco. Ainda assim, é uma exceção deliberada à política geral do projeto de não persistir texto de vaga/currículo entre requisições (ver Segurança). Para desativar num deploy específico, instancie os providers com `AsyncLRUCache(maxsize=0)` (nunca retém nada de uma chamada para a outra) em vez do padrão `DEFAULT_MAXSIZE=128`.

---

## Versionamento

O currículo base é imutável (modelos Pydantic `frozen=True`). Cada vaga gera uma nova versão derivada:

```
Base Resume (BASE-v1)          (nunca modificado)
    ├─► Vaga Nubank ─► #001 balanced + #002 ats_focus + #003 experience_focus
    └─► Vaga Itaú   ─► #004 balanced + #005 ats_focus + #006 experience_focus
```

O pipeline compara um snapshot do base antes e depois e expõe `base_resume_untouched` em toda resposta.

---

## PDF

Gerado com **ReportLab**, nunca como screenshot:

- texto real e selecionável
- uma página, coluna única
- Helvetica (fonte padrão, sem `/FontFile` embutido)
- links clicáveis mantendo o rótulo textual
- sem tabelas, ícones ou imagens
- sem scores ou metadados internos da IA

Nome do arquivo (regra 15 — curto, sem cargo/score/versão/timestamp): `curriculo-caio-[empresa].pdf`, degradando para `curriculo-caio.pdf` quando não há empresa. Ex.: `curriculo-caio-microsoft.pdf`.

---

## Testes

```bash
cd backend && pytest        # ~108 testes
cd frontend && npx tsc --noEmit
```

Cobrem: análise da vaga, matching, aliases/taxonomia, proteção contra tecnologias inexistentes, confirmação de gaps (sim/não/não-tenho-certeza e seus efeitos no matching e na versão adaptada), geração das 3 estratégias e sua não-remoção/não-invenção de conteúdo, recomendação entre as 3 versões, validação factual, auto-correção, detecção de arquétipo, redações de resumo (todas passam pelo FactualGuard), imutabilidade do currículo base mesmo com confirmações, reanálise recalculando match+validação+recomendação juntos, geração e estrutura do PDF, nome de arquivo curto, vaga muito longa (>30k caracteres), vaga sem tecnologias, e a camada HTTP.

> Duas suítes de `test_ai_factory.py` (`test_provider_padrao_com_chave_e_anthropic`, `test_provider_gemini`) podem falhar neste ambiente por incompatibilidade de versão entre os SDKs `anthropic`/`google-genai` instalados e `httpx` — é um problema de dependências pré-existente, não relacionado à lógica do CV Matcher.

---

## Segurança

- Chaves de IA vivem **apenas no backend**, lidas de `.env` via `pydantic-settings`. O frontend nunca as recebe.
- `.env` está no `.gitignore`; use `.env.example` como referência.
- CORS restrito às origens de `CORS_ORIGINS`.
- O histórico em memória guarda **apenas metadados** — descrições de vaga e textos de currículo não são persistidos.
