"""CURRICULO BASE OFICIAL - VERSAO IMUTAVEL.

Este objeto e a unica fonte de verdade factual do sistema. Nenhuma parte da
aplicacao pode altera-lo: adaptacoes sempre produzem novas versoes derivadas.
Qualquer informacao que nao esteja aqui e considerada alucinacao.
"""

from __future__ import annotations

from app.resume.models import (
    Resume,
    ResumeBasics,
    ResumeCourse,
    ResumeEducation,
    ResumeExperience,
    ResumeExperienceBullet,
    ResumeLanguage,
    ResumeLink,
    ResumeProject,
    ResumeProjectBullet,
    ResumeSkillCategory,
    ResumeSummaryTemplate,
    SummaryFragment,
)

BASE_RESUME = Resume(
    id="base",
    version="BASE-v1",
    kind="base",
    basics=ResumeBasics(
        name="Caio Lucas Silva Gomes",
        headline="Desenvolvedor Full Stack",
        location="São Paulo, Brasil",
        email="caiolucasxz55@gmail.com",
        phone="(11) 91281-7389",
        links=(
            ResumeLink(label="GitHub", url="https://github.com/"),
            ResumeLink(label="LinkedIn", url="https://www.linkedin.com/"),
            ResumeLink(label="Portfólio", url="https://portfolio.example.com/"),
        ),
    ),
    summary=(
        "Desenvolvedor Full Stack com experiência no desenvolvimento e evolução de "
        "aplicações web utilizando Python, FastAPI, Next.js e TypeScript. Experiência "
        "em desenvolvimento de APIs REST, integração de soluções de Inteligência "
        "Artificial e Machine Learning, CI/CD e Cloud Computing. Atuação com foco em "
        "segurança, performance, escalabilidade e boas práticas de engenharia de software."
    ),
    experience=(
        ResumeExperience(
            id="exp-inoltra",
            role="Desenvolvedor Full Stack Júnior",
            company="Inoltra-Tech",
            location="São Paulo, Brasil",
            period="Jan 2026 – Agosto 2026",
            current=False,
            bullets=(
                ResumeExperienceBullet(
                    id="exp-inoltra-b1",
                    text=(
                        "Responsável pelo desenvolvimento completo do frontend de uma das "
                        "principais soluções da empresa, aprimorando UI/UX, usabilidade e "
                        "experiência dos usuários desde a estruturação inicial até a evolução "
                        "contínua do produto."
                    ),
                    terms=("Frontend", "UI/UX", "Usabilidade"),
                ),
                ResumeExperienceBullet(
                    id="exp-inoltra-b2",
                    text=(
                        "Desenvolvimento e otimização de funcionalidades e regras de negócio "
                        "no backend com Python/FastAPI, priorizando segurança, performance e "
                        "confiabilidade."
                    ),
                    terms=("Backend", "Python", "FastAPI", "Segurança", "Performance"),
                ),
                ResumeExperienceBullet(
                    id="exp-inoltra-b3",
                    text=(
                        "Desenvolvimento de arquitetura RAG (Retrieval-Augmented Generation) "
                        "integrada a chatbots e modelos de IA, reduzindo significativamente o "
                        "consumo e custo de tokens da principal solução da empresa."
                    ),
                    terms=("RAG", "Chatbots", "LLMs", "Machine Learning", "Arquitetura de Software"),
                ),
                ResumeExperienceBullet(
                    id="exp-inoltra-b4",
                    text=(
                        "Integração de tecnologia comercial de Eye Tracking à plataforma, "
                        "adicionando uma funcionalidade inovadora e diferencial ao produto."
                    ),
                    terms=("Eye Tracking", "Integração de APIs"),
                ),
                ResumeExperienceBullet(
                    id="exp-inoltra-b5",
                    text=(
                        "Contribuição na evolução dos processos de CI/CD, aumentando a "
                        "segurança, padronização e confiabilidade do fluxo de desenvolvimento "
                        "e entrega em equipe."
                    ),
                    terms=("CI/CD", "DevOps", "Segurança"),
                ),
                ResumeExperienceBullet(
                    id="exp-inoltra-b6",
                    text=(
                        "Implementação e self-hosting da solução de IA/RAG na Microsoft Azure, "
                        "atuando na infraestrutura e nos requisitos de DevOps, segurança e "
                        "deployment necessários para sua operação."
                    ),
                    terms=("Azure", "Self-hosting", "DevOps", "RAG", "Segurança", "Cloud"),
                ),
            ),
        ),
    ),
    projects=(
        ResumeProject(
            id="proj-smart-guide",
            name="Smart Guide — Planejador de Rotas do Metrô de São Paulo",
            description=(
                "Aplicação web interativa que facilita o planejamento de rotas no sistema "
                "metroviário de São Paulo. Com foco em acessibilidade e usabilidade, permite "
                "visualizar estações, calcular rotas eficientes, salvar trajetos favoritos e "
                "consultar informações detalhadas de cada estação."
            ),
            terms=("Frontend", "Usabilidade", "Acessibilidade"),
            bullets=(
                ResumeProjectBullet(
                    id="proj-smart-guide-b1",
                    text="Frontend desenvolvido em React e Next.js, com JavaScript.",
                    terms=("React", "Next.js", "JavaScript", "Frontend"),
                ),
                ResumeProjectBullet(
                    id="proj-smart-guide-b2",
                    text="Backend em Java com Spring Boot.",
                    terms=("Java", "Spring Boot", "Backend"),
                ),
                ResumeProjectBullet(
                    id="proj-smart-guide-b3",
                    text="Código versionado com Git.",
                    terms=("Git",),
                ),
            ),
        ),
    ),
    skill_categories=(
        ResumeSkillCategory(
            id="skills-frontend",
            label="Frontend",
            items=("TypeScript", "JavaScript", "React", "Next.js", "Angular"),
        ),
        ResumeSkillCategory(
            id="skills-backend",
            label="Backend",
            items=("Python", "FastAPI", "Node.js", "Java", "Flask", "REST APIs"),
        ),
        ResumeSkillCategory(
            id="skills-data",
            label="Bancos",
            items=("PostgreSQL", "MySQL", "MongoDB", "Oracle SQL"),
        ),
        ResumeSkillCategory(
            id="skills-ai",
            label="IA / Machine Learning",
            items=(
                "LLMs",
                "RAG",
                "Chatbots",
                "Machine Learning",
                "Integração e treinamento de modelos",
            ),
        ),
        ResumeSkillCategory(
            id="skills-cloud",
            label="Cloud / DevOps",
            items=(
                "Azure",
                "AWS",
                "Docker",
                "CI/CD",
                "GitHub Actions",
            ),
        ),
        ResumeSkillCategory(
            id="skills-eng",
            label="Engenharia",
            items=(
                "Git",
                "GitHub",
                "Clean Code",
                "Arquitetura de Software",
                "Integração de APIs",
            ),
        ),
    ),
    education=(
        ResumeEducation(
            id="edu-fiap",
            degree="Tecnólogo em Análise e Desenvolvimento de Sistemas",
            institution="FIAP – Centro Universitário",
            period="Conclusão: Jul 2026",
        ),
    ),
    courses=(
        ResumeCourse(
            id="course-azure",
            name="Azure Cloud: criação de servidor e banco de dados",
            terms=("Azure", "Cloud"),
        ),
        ResumeCourse(id="course-react-ts", name="React + TypeScript", terms=("React", "TypeScript")),
        ResumeCourse(id="course-node-n8n", name="Node.js e N8N", terms=("Node.js", "N8N")),
        ResumeCourse(id="course-python-ia", name="Python + IA", terms=("Python", "Machine Learning")),
        ResumeCourse(
            id="course-js-ts",
            name="JavaScript e TypeScript",
            terms=("JavaScript", "TypeScript"),
        ),
    ),
    languages=(
        ResumeLanguage(name="Inglês", level="Avançado"),
        ResumeLanguage(name="Espanhol", level="Intermediário"),
    ),
    # Fragmentos aprovados para recomposicao do resumo. Todo texto abaixo e
    # derivado diretamente do resumo profissional do curriculo base.
    summary_template=ResumeSummaryTemplate(
        role="Desenvolvedor Full Stack",
        opening="com experiência no desenvolvimento e evolução de aplicações web utilizando",
        capabilities=(
            SummaryFragment(
                id="cap-apis",
                text="desenvolvimento de APIs REST",
                terms=("REST APIs", "Backend"),
            ),
            SummaryFragment(
                id="cap-ia",
                text="integração de soluções de Inteligência Artificial e Machine Learning",
                terms=("Machine Learning", "LLMs", "RAG", "Chatbots"),
            ),
            SummaryFragment(id="cap-cicd", text="CI/CD", terms=("CI/CD", "DevOps")),
            SummaryFragment(id="cap-cloud", text="Cloud Computing", terms=("Cloud", "Azure", "AWS")),
            SummaryFragment(
                id="cap-frontend",
                text="construção de interfaces com foco em UI/UX e usabilidade",
                terms=("Frontend", "UI/UX", "Usabilidade", "React", "Next.js"),
            ),
            SummaryFragment(
                id="cap-infra",
                text="infraestrutura e self-hosting de aplicações em nuvem",
                terms=("Self-hosting", "Azure", "DevOps", "Docker"),
            ),
        ),
        focus=(
            SummaryFragment(id="foc-sec", text="segurança", terms=("Segurança",)),
            SummaryFragment(id="foc-perf", text="performance", terms=("Performance",)),
            SummaryFragment(id="foc-scale", text="escalabilidade", terms=("Escalabilidade",)),
            SummaryFragment(
                id="foc-best",
                text="boas práticas de engenharia de software",
                terms=("Clean Code", "Arquitetura de Software"),
            ),
        ),
        fallback=(
            "Desenvolvedor Full Stack com experiência no desenvolvimento e evolução de "
            "aplicações web, atuando em frontend e backend com foco em segurança, "
            "performance, escalabilidade e boas práticas de engenharia de software."
        ),
    ),
)
