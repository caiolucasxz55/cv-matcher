"""Arquetipos de perfil profissional.

Cada arquetipo carrega redacoes de resumo ESCRITAS A MAO, derivadas apenas de
fatos que existem no curriculo base. Assim como `summary_template`, este
modulo e DADO IMUTAVEL do autor — nao e texto gerado por IA.

O `{techs}` de cada redacao e preenchido dinamicamente com as tecnologias que
(a) pertencem ao pool do arquetipo, (b) tem evidencia real no curriculo base e
(c) sao relevantes para a vaga. Nada entra sem evidencia.

Um arquetipo so fica disponivel se seus `required_terms` tiverem evidencia —
por isso nao existe arquetipo de "Dados": os bancos aparecem apenas como
habilidade declarada, nunca em experiencia profissional.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ArchetypeSummaryVariant:
    id: str
    label: str
    #: Redação com o marcador {techs}. Texto do autor, nunca gerado.
    template: str
    #: Termos que precisam ter evidência para esta redação ser oferecida.
    required_terms: tuple[str, ...]


@dataclass(frozen=True)
class Archetype:
    id: str
    label: str
    description: str
    #: Termos da vaga que ativam este arquetipo.
    signals: tuple[str, ...]
    #: Tecnologias candidatas a preencher {techs}, em ordem de preferencia.
    tech_pool: tuple[str, ...]
    variants: tuple[ArchetypeSummaryVariant, ...]


ARCHETYPES: tuple[Archetype, ...] = (
    Archetype(
        id="frontend",
        label="Frontend",
        description="Vagas centradas em interface, UI/UX e aplicações web no cliente.",
        signals=(
            "Frontend",
            "React",
            "Next.js",
            "TypeScript",
            "JavaScript",
            "Angular",
            "UI/UX",
            "Usabilidade",
            "Acessibilidade",
            "Tailwind CSS",
            "Vue",
        ),
        tech_pool=("TypeScript", "React", "Next.js", "JavaScript", "Angular"),
        variants=(
            ArchetypeSummaryVariant(
                id="frontend-conciso",
                label="Conciso",
                template=(
                    "Desenvolvedor Full Stack com experiência no desenvolvimento completo do "
                    "frontend de aplicações web, utilizando {techs}. Atuação em UI/UX, "
                    "usabilidade e experiência dos usuários, desde a estruturação inicial até "
                    "a evolução contínua do produto. Foco em performance, escalabilidade e "
                    "boas práticas de engenharia de software."
                ),
                required_terms=("Frontend", "UI/UX", "Usabilidade"),
            ),
            ArchetypeSummaryVariant(
                id="frontend-completo",
                label="Completo",
                template=(
                    "Desenvolvedor Full Stack responsável pelo desenvolvimento completo do "
                    "frontend de uma das principais soluções da empresa, utilizando {techs}. "
                    "Experiência em UI/UX, usabilidade e integração de APIs REST, com atuação "
                    "também no backend com Python e FastAPI. Foco em performance, segurança e "
                    "boas práticas de engenharia de software."
                ),
                required_terms=("Frontend", "UI/UX", "REST APIs", "Python", "FastAPI"),
            ),
        ),
    ),
    Archetype(
        id="backend",
        label="Backend",
        description="Vagas centradas em APIs, regras de negócio e serviços no servidor.",
        signals=(
            "Backend",
            "Python",
            "FastAPI",
            "REST APIs",
            "Node.js",
            "Java",
            "Flask",
            "Django",
            "Spring Boot",
            "PostgreSQL",
            "MySQL",
            "MongoDB",
            "Segurança",
            "Performance",
            "Escalabilidade",
        ),
        tech_pool=("Python", "FastAPI", "REST APIs", "Node.js", "Java", "Flask"),
        variants=(
            ArchetypeSummaryVariant(
                id="backend-conciso",
                label="Conciso",
                template=(
                    "Desenvolvedor Full Stack com experiência no desenvolvimento e evolução de "
                    "aplicações web utilizando {techs}. Experiência em desenvolvimento de APIs "
                    "REST, regras de negócio e integração de soluções de Inteligência "
                    "Artificial e Machine Learning. Atuação com foco em segurança, performance, "
                    "escalabilidade e boas práticas de engenharia de software."
                ),
                required_terms=("Backend", "Python", "FastAPI", "REST APIs"),
            ),
            ArchetypeSummaryVariant(
                id="backend-infra",
                label="Com ênfase em entrega",
                template=(
                    "Desenvolvedor Full Stack com atuação em backend utilizando {techs}, no "
                    "desenvolvimento e otimização de funcionalidades e regras de negócio. "
                    "Experiência em APIs REST, CI/CD e Cloud Computing, priorizando segurança, "
                    "performance e confiabilidade."
                ),
                required_terms=("Backend", "Python", "FastAPI", "CI/CD", "Cloud"),
            ),
        ),
    ),
    Archetype(
        id="fullstack",
        label="Full Stack",
        description="Vagas que cobrem frontend e backend na mesma posição.",
        signals=(
            "Full Stack",
            "Frontend",
            "Backend",
            "TypeScript",
            "Python",
            "React",
            "Next.js",
            "FastAPI",
            "REST APIs",
            "Node.js",
        ),
        tech_pool=("Python", "FastAPI", "Next.js", "TypeScript", "React", "Node.js"),
        variants=(
            ArchetypeSummaryVariant(
                id="fullstack-padrao",
                label="Padrão",
                template=(
                    "Desenvolvedor Full Stack com experiência no desenvolvimento e evolução de "
                    "aplicações web utilizando {techs}. Experiência em desenvolvimento de APIs "
                    "REST, integração de soluções de Inteligência Artificial e Machine "
                    "Learning, CI/CD e Cloud Computing. Atuação com foco em segurança, "
                    "performance, escalabilidade e boas práticas de engenharia de software."
                ),
                required_terms=("Frontend", "Backend", "REST APIs"),
            ),
            ArchetypeSummaryVariant(
                id="fullstack-ponta-a-ponta",
                label="Ponta a ponta",
                template=(
                    "Desenvolvedor Full Stack com atuação de ponta a ponta em aplicações web, "
                    "do frontend à infraestrutura, utilizando {techs}. Experiência em UI/UX, "
                    "APIs REST, integração de modelos de IA, CI/CD e Cloud Computing. Foco em "
                    "segurança, performance, escalabilidade e boas práticas de engenharia de "
                    "software."
                ),
                required_terms=("Frontend", "Backend", "UI/UX", "Cloud", "CI/CD"),
            ),
        ),
    ),
    Archetype(
        id="devops",
        label="DevOps / Cloud",
        description="Vagas de infraestrutura, nuvem, containers e pipelines de entrega.",
        signals=(
            "DevOps",
            "Azure",
            "AWS",
            "Cloud",
            "Docker",
            "Kubernetes",
            "CI/CD",
            "GitHub Actions",
            "Self-hosting",
            "Terraform",
            "Linux",
            "Observabilidade",
            "Azure Web Apps",
            "Azure Container Registry",
        ),
        tech_pool=("Azure", "AWS", "Docker", "CI/CD", "GitHub Actions", "Self-hosting"),
        variants=(
            ArchetypeSummaryVariant(
                id="devops-conciso",
                label="Conciso",
                template=(
                    "Desenvolvedor Full Stack com experiência em Cloud Computing e DevOps, "
                    "utilizando {techs}. Atuação na implementação e self-hosting de soluções em "
                    "nuvem, na evolução de processos de CI/CD e nos requisitos de "
                    "infraestrutura, segurança e deployment. Foco em confiabilidade, "
                    "padronização e boas práticas de engenharia de software."
                ),
                required_terms=("Azure", "CI/CD", "Self-hosting", "DevOps"),
            ),
            ArchetypeSummaryVariant(
                id="devops-infra",
                label="Ênfase em infraestrutura",
                template=(
                    "Desenvolvedor Full Stack com atuação em infraestrutura e DevOps utilizando "
                    "{techs}. Experiência em self-hosting de solução de IA em nuvem, "
                    "containerização e evolução de pipelines de CI/CD, aumentando segurança, "
                    "padronização e confiabilidade do fluxo de desenvolvimento e entrega."
                ),
                required_terms=("Azure", "Docker", "CI/CD", "Self-hosting", "RAG"),
            ),
        ),
    ),
    Archetype(
        id="ai_ml",
        label="IA / Machine Learning",
        description="Vagas de IA aplicada, LLMs, RAG e integração de modelos.",
        signals=(
            "Machine Learning",
            "LLMs",
            "RAG",
            "Chatbots",
            "Vector Database",
            "Prompt Engineering",
            "Deep Learning",
            "Eye Tracking",
            "Integração e treinamento de modelos",
            "Python",
        ),
        tech_pool=("Python", "RAG", "LLMs", "Chatbots", "Machine Learning", "FastAPI"),
        variants=(
            ArchetypeSummaryVariant(
                id="ai-conciso",
                label="Conciso",
                template=(
                    "Desenvolvedor Full Stack com experiência em integração de soluções de "
                    "Inteligência Artificial e Machine Learning, utilizando {techs}. Atuação no "
                    "desenvolvimento de arquitetura RAG integrada a chatbots e modelos de IA, "
                    "reduzindo o consumo e custo de tokens. Foco em segurança, performance e "
                    "boas práticas de engenharia de software."
                ),
                required_terms=("RAG", "Chatbots", "LLMs", "Machine Learning"),
            ),
            ArchetypeSummaryVariant(
                id="ai-aplicada",
                label="IA aplicada + infraestrutura",
                template=(
                    "Desenvolvedor Full Stack com atuação em IA aplicada utilizando {techs}. "
                    "Experiência em arquitetura RAG, chatbots e integração de modelos, além do "
                    "self-hosting da solução de IA na Microsoft Azure, atuando nos requisitos "
                    "de DevOps, segurança e deployment necessários para sua operação."
                ),
                required_terms=("RAG", "Chatbots", "Azure", "Self-hosting", "DevOps"),
            ),
        ),
    ),
)


def all_archetype_texts() -> tuple[str, ...]:
    """Todo o texto declarado pelo autor, para absorcao no vocabulario base."""
    return tuple(
        variant.template.replace("{techs}", "")
        for archetype in ARCHETYPES
        for variant in archetype.variants
    )


def get_archetype(archetype_id: str) -> Archetype | None:
    return next((item for item in ARCHETYPES if item.id == archetype_id), None)
