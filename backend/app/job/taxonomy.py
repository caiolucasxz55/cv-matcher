"""Taxonomia canonica de tecnologias e competencias.

Usada para (1) extrair termos da descricao da vaga de forma deterministica e
(2) normalizar sinonimos antes do matching. `related` alimenta o nivel de match
FRACO: um conceito relacionado NUNCA e adicionado ao curriculo, apenas reportado.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Literal

TermCategory = Literal[
    "language", "framework", "database", "cloud", "devops", "ai_ml", "tool", "competency"
]


@dataclass(frozen=True)
class TaxonomyEntry:
    canonical: str
    category: TermCategory
    aliases: tuple[str, ...] = ()
    related: tuple[str, ...] = ()


TAXONOMY: tuple[TaxonomyEntry, ...] = (
    # ------------------------------------------------------------- linguagens
    TaxonomyEntry("Python", "language", ("python", "python3")),
    TaxonomyEntry("TypeScript", "language", ("typescript", "type script", "ts"), ("JavaScript",)),
    TaxonomyEntry(
        "JavaScript", "language", ("javascript", "java script", "js", "ecmascript"), ("TypeScript",)
    ),
    TaxonomyEntry("Java", "language", ("java",)),
    TaxonomyEntry("C#", "language", ("c#", "csharp", "c sharp"), ("Java",)),
    TaxonomyEntry("Go", "language", ("golang",)),
    TaxonomyEntry("PHP", "language", ("php",)),
    TaxonomyEntry("Ruby", "language", ("ruby",)),
    TaxonomyEntry("Kotlin", "language", ("kotlin",)),
    TaxonomyEntry("Rust", "language", ("rust",)),
    TaxonomyEntry("SQL", "language", ("sql",)),
    # ------------------------------------------------------------- frameworks
    TaxonomyEntry("React", "framework", ("react", "react.js", "reactjs")),
    TaxonomyEntry("Next.js", "framework", ("next.js", "nextjs", "next js")),
    TaxonomyEntry("Angular", "framework", ("angular", "angularjs")),
    TaxonomyEntry("Vue", "framework", ("vue", "vue.js", "vuejs"), ("React", "Angular")),
    TaxonomyEntry("Svelte", "framework", ("svelte",), ("React",)),
    TaxonomyEntry("Node.js", "framework", ("node.js", "nodejs", "node")),
    TaxonomyEntry("FastAPI", "framework", ("fastapi", "fast api")),
    TaxonomyEntry("Flask", "framework", ("flask",)),
    TaxonomyEntry("Django", "framework", ("django",), ("Flask", "FastAPI")),
    TaxonomyEntry("Spring Boot", "framework", ("spring boot", "springboot", "spring"), ("Java",)),
    TaxonomyEntry("Express", "framework", ("express", "express.js", "expressjs"), ("Node.js",)),
    TaxonomyEntry("NestJS", "framework", ("nestjs", "nest.js"), ("Node.js",)),
    TaxonomyEntry(".NET", "framework", (".net", "dotnet", "asp.net"), ("C#",)),
    TaxonomyEntry("Tailwind CSS", "framework", ("tailwind", "tailwind css", "tailwindcss")),
    TaxonomyEntry(
        "REST APIs",
        "competency",
        ("rest", "restful", "rest api", "rest apis", "api rest", "apis rest", "api restful"),
    ),
    TaxonomyEntry("GraphQL", "framework", ("graphql",), ("REST APIs",)),
    TaxonomyEntry("gRPC", "framework", ("grpc",), ("REST APIs",)),
    # ----------------------------------------------------------------- bancos
    TaxonomyEntry("PostgreSQL", "database", ("postgresql", "postgres", "psql")),
    TaxonomyEntry("MySQL", "database", ("mysql",)),
    TaxonomyEntry("MongoDB", "database", ("mongodb", "mongo")),
    TaxonomyEntry("Oracle SQL", "database", ("oracle sql", "oracle", "pl/sql", "plsql")),
    TaxonomyEntry("Redis", "database", ("redis",), ("MongoDB",)),
    TaxonomyEntry(
        "SQL Server", "database", ("sql server", "sqlserver", "t-sql"), ("MySQL", "PostgreSQL")
    ),
    TaxonomyEntry("Elasticsearch", "database", ("elasticsearch", "elastic search", "opensearch")),
    TaxonomyEntry("DynamoDB", "database", ("dynamodb",), ("MongoDB", "AWS")),
    # ------------------------------------------------------------------ cloud
    TaxonomyEntry("Azure", "cloud", ("azure", "microsoft azure")),
    TaxonomyEntry("AWS", "cloud", ("aws", "amazon web services")),
    TaxonomyEntry(
        "GCP", "cloud", ("gcp", "google cloud", "google cloud platform"), ("Azure", "AWS")
    ),
    TaxonomyEntry("Cloud", "cloud", ("cloud", "cloud computing", "computação em nuvem", "nuvem")),
    TaxonomyEntry("Azure Web Apps", "cloud", ("azure web apps", "azure app service")),
    TaxonomyEntry("Azure Container Registry", "cloud", ("azure container registry", "acr")),
    TaxonomyEntry(
        "Self-hosting",
        "cloud",
        ("self-hosting", "self hosting", "selfhosted", "self-hosted", "on-premise", "on premise"),
    ),
    TaxonomyEntry(
        "Serverless",
        "cloud",
        ("serverless", "lambda", "aws lambda", "azure functions"),
        ("AWS", "Azure"),
    ),
    # ----------------------------------------------------------------- devops
    TaxonomyEntry(
        "Docker", "devops", ("docker", "containers", "containerização", "containerizacao")
    ),
    TaxonomyEntry("Kubernetes", "devops", ("kubernetes", "k8s", "eks", "aks"), ("Docker",)),
    TaxonomyEntry(
        "CI/CD",
        "devops",
        (
            "ci/cd",
            "ci cd",
            "cicd",
            "integração contínua",
            "integracao continua",
            "entrega contínua",
            "continuous integration",
            "continuous delivery",
        ),
    ),
    TaxonomyEntry("GitHub Actions", "devops", ("github actions",), ("CI/CD",)),
    TaxonomyEntry("GitLab CI", "devops", ("gitlab ci", "gitlab-ci"), ("CI/CD",)),
    TaxonomyEntry("Jenkins", "devops", ("jenkins",), ("CI/CD",)),
    TaxonomyEntry(
        "Terraform", "devops", ("terraform", "iac", "infrastructure as code"), ("Cloud",)
    ),
    TaxonomyEntry("DevOps", "devops", ("devops",)),
    TaxonomyEntry("Linux", "devops", ("linux", "unix", "shell script", "bash")),
    TaxonomyEntry(
        "Observabilidade",
        "devops",
        (
            "observabilidade",
            "observability",
            "monitoramento",
            "monitoring",
            "grafana",
            "prometheus",
            "datadog",
        ),
    ),
    TaxonomyEntry(
        "Kafka", "devops", ("kafka", "rabbitmq", "mensageria", "message broker", "filas")
    ),
    # ----------------------------------------------------------------- IA/ML
    TaxonomyEntry(
        "Machine Learning",
        "ai_ml",
        (
            "machine learning",
            "aprendizado de máquina",
            "aprendizado de maquina",
            "ml",
            "inteligência artificial",
            "inteligencia artificial",
            "ia",
            "artificial intelligence",
            "ai",
        ),
    ),
    TaxonomyEntry(
        "LLMs",
        "ai_ml",
        (
            "llm",
            "llms",
            "large language model",
            "large language models",
            "modelos de linguagem",
            "gpt",
            "openai",
            "claude",
            "gemini",
        ),
    ),
    TaxonomyEntry(
        "RAG",
        "ai_ml",
        ("rag", "retrieval-augmented generation", "retrieval augmented generation"),
    ),
    TaxonomyEntry(
        "Chatbots",
        "ai_ml",
        ("chatbot", "chatbots", "agentes conversacionais", "assistente virtual"),
    ),
    TaxonomyEntry("Eye Tracking", "ai_ml", ("eye tracking", "eye-tracking", "rastreamento ocular")),
    TaxonomyEntry(
        "Vector Database",
        "ai_ml",
        ("vector database", "banco vetorial", "embeddings", "pinecone", "pgvector", "chroma"),
        ("RAG",),
    ),
    TaxonomyEntry(
        "Prompt Engineering", "ai_ml", ("prompt engineering", "engenharia de prompt"), ("LLMs",)
    ),
    TaxonomyEntry(
        "Deep Learning",
        "ai_ml",
        ("deep learning", "redes neurais", "pytorch", "tensorflow"),
        ("Machine Learning",),
    ),
    TaxonomyEntry(
        "Integração e treinamento de modelos",
        "ai_ml",
        ("treinamento de modelos", "fine-tuning", "fine tuning", "model training"),
    ),
    # ------------------------------------------------------------ ferramentas
    TaxonomyEntry(
        "Git", "tool", ("git", "versionamento", "controle de versão", "controle de versao")
    ),
    TaxonomyEntry("GitHub", "tool", ("github",)),
    TaxonomyEntry("N8N", "tool", ("n8n",)),
    TaxonomyEntry("Jira", "tool", ("jira",)),
    TaxonomyEntry("Figma", "tool", ("figma",)),
    TaxonomyEntry("Automação", "tool", ("automação", "automacao", "automation")),
    # ----------------------------------------------------------- competencias
    TaxonomyEntry("Frontend", "competency", ("frontend", "front-end", "front end")),
    TaxonomyEntry("Backend", "competency", ("backend", "back-end", "back end")),
    TaxonomyEntry("Full Stack", "competency", ("full stack", "fullstack", "full-stack")),
    TaxonomyEntry(
        "UI/UX",
        "competency",
        ("ui/ux", "ui ux", "ux", "ui", "user experience", "design de interface"),
    ),
    TaxonomyEntry("Usabilidade", "competency", ("usabilidade", "usability")),
    TaxonomyEntry(
        "Acessibilidade", "competency", ("acessibilidade", "accessibility", "wcag", "a11y")
    ),
    TaxonomyEntry(
        "Segurança",
        "competency",
        (
            "segurança",
            "seguranca",
            "security",
            "appsec",
            "owasp",
            "autenticação",
            "autenticacao",
            "oauth",
            "jwt",
        ),
    ),
    TaxonomyEntry(
        "Performance", "competency", ("performance", "desempenho", "otimização", "otimizacao")
    ),
    TaxonomyEntry(
        "Escalabilidade", "competency", ("escalabilidade", "scalability", "escalável", "escalavel")
    ),
    TaxonomyEntry(
        "Clean Code",
        "competency",
        ("clean code", "código limpo", "codigo limpo", "boas práticas", "boas praticas", "solid"),
    ),
    TaxonomyEntry(
        "Arquitetura de Software",
        "competency",
        (
            "arquitetura de software",
            "arquitetura",
            "software architecture",
            "microserviços",
            "microservicos",
            "microservices",
            "design patterns",
        ),
    ),
    TaxonomyEntry(
        "Integração de APIs",
        "competency",
        (
            "integração de apis",
            "integracao de apis",
            "integrações",
            "integracoes",
            "api integration",
        ),
    ),
    TaxonomyEntry(
        "Testes",
        "competency",
        (
            "testes",
            "testing",
            "testes unitários",
            "testes unitarios",
            "unit tests",
            "tdd",
            "jest",
            "pytest",
            "vitest",
        ),
    ),
    TaxonomyEntry(
        "Metodologias Ágeis",
        "competency",
        (
            "ágil",
            "agil",
            "agile",
            "scrum",
            "kanban",
            "metodologias ágeis",
            "metodologias ageis",
        ),
    ),
    TaxonomyEntry(
        "Inglês",
        "competency",
        ("inglês", "ingles", "english", "inglês avançado", "ingles avancado"),
    ),
    TaxonomyEntry("Espanhol", "competency", ("espanhol", "spanish")),
)


def normalize_term(value: str) -> str:
    """Minusculas + remocao de acentos + colapso de espacos."""
    lowered = value.lower()
    decomposed = unicodedata.normalize("NFD", lowered)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", stripped).strip()


_BY_CANONICAL: dict[str, TaxonomyEntry] = {entry.canonical.lower(): entry for entry in TAXONOMY}


@dataclass(frozen=True)
class _AliasRef:
    alias: str
    canonical: str
    pattern: re.Pattern[str] = field(compare=False)


def _build_alias_index() -> tuple[_AliasRef, ...]:
    refs: list[_AliasRef] = []
    for entry in TAXONOMY:
        for alias in (entry.canonical, *entry.aliases):
            normalized = normalize_term(alias)
            if not normalized:
                continue
            # Fronteira de palavra tolerante a `.`, `#`, `+` e `/` — necessario
            # para termos como `Node.js`, `C#`, `CI/CD` e `.NET`.
            pattern = re.compile(
                r"(?<![a-z0-9+#/._-])" + re.escape(normalized) + r"(?![a-z0-9+#_-])"
            )
            refs.append(_AliasRef(normalized, entry.canonical, pattern))
    # Aliases mais longos primeiro: evita que "node" mascare "node.js".
    refs.sort(key=lambda ref: len(ref.alias), reverse=True)
    return tuple(refs)


_ALIAS_INDEX = _build_alias_index()
_ALIAS_TO_CANONICAL: dict[str, str] = {ref.alias: ref.canonical for ref in _ALIAS_INDEX}


def get_taxonomy_entry(canonical: str) -> TaxonomyEntry | None:
    return _BY_CANONICAL.get(canonical.lower())


def get_category(canonical: str) -> TermCategory:
    entry = get_taxonomy_entry(canonical)
    return entry.category if entry else "competency"


def get_related(canonical: str) -> tuple[str, ...]:
    entry = get_taxonomy_entry(canonical)
    return entry.related if entry else ()


def resolve_canonical(value: str) -> str | None:
    """Resolve texto livre para termo canonico, se houver alias exato."""
    return _ALIAS_TO_CANONICAL.get(normalize_term(value))


@dataclass(frozen=True)
class DetectedTerm:
    canonical: str
    category: TermCategory
    occurrences: int


@lru_cache(maxsize=256)
def _detect_terms_cached(text: str) -> tuple[DetectedTerm, ...]:
    return tuple(_detect_terms_impl(text))


def _detect_terms_impl(text: str) -> list[DetectedTerm]:
    normalized = normalize_term(text)
    counts: dict[str, int] = {}
    consumed = bytearray(len(normalized))

    for ref in _ALIAS_INDEX:
        for match in ref.pattern.finditer(normalized):
            start, end = match.span()
            if any(consumed[start:end]):
                continue
            consumed[start:end] = b"\x01" * (end - start)
            counts[ref.canonical] = counts.get(ref.canonical, 0) + 1

    detected = [
        DetectedTerm(canonical, get_category(canonical), occurrences)
        for canonical, occurrences in counts.items()
    ]
    detected.sort(key=lambda item: (-item.occurrences, item.canonical))
    return detected


def detect_terms(text: str) -> list[DetectedTerm]:
    """Extrai termos canonicos de texto livre. Deterministico, sem IA."""
    if len(text) <= 8_000:
        return list(_detect_terms_cached(text))
    return _detect_terms_impl(text)


def all_canonical_terms() -> tuple[str, ...]:
    return tuple(entry.canonical for entry in TAXONOMY)
