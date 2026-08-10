BACKEND_PYTHON_JOB = """Desenvolvedor Backend Python Pleno

Sobre a empresa
Somos uma fintech em crescimento acelerado.

Responsabilidades
- Desenvolver e manter APIs REST de alta disponibilidade.
- Implementar regras de negócio no backend com foco em segurança e performance.
- Participar da evolução dos processos de CI/CD do time.

Requisitos obrigatórios
- Experiência sólida com Python e FastAPI.
- Domínio de APIs REST.
- Experiência com Docker.
- Conhecimento em PostgreSQL.

Diferenciais
- Experiência com AWS.
- Vivência com Kubernetes.
- Conhecimento em Terraform.

Benefícios
- Vale refeição, plano de saúde e day off no aniversário.
"""

FRONTEND_REACT_JOB = """Pessoa Desenvolvedora Frontend React

O que você vai fazer
- Construir interfaces com React e Next.js.
- Cuidar da usabilidade e da experiência do usuário.

Requisitos
- TypeScript e JavaScript são obrigatórios.
- Experiência com React.
- Conhecimento de UI/UX.

Desejável
- Next.js.
- Acessibilidade (WCAG).
"""

CLOUD_DEVOPS_JOB = """Engenheiro DevOps / Cloud

Requisitos obrigatórios
- Azure ou AWS.
- Docker é essencial.
- CI/CD com GitHub Actions.
- Self-hosting de aplicações.

Diferenciais
- Kubernetes.
- Terraform.
"""

NO_TECH_JOB = """Analista Administrativo Júnior

Responsabilidades
- Organizar documentos e planilhas do setor.
- Atender fornecedores por telefone.

Requisitos
- Ensino médio completo.
- Boa comunicação e organização.

Benefícios
- Vale transporte.
"""


def build_very_long_job() -> str:
    """Vaga muito longa: valida o limite de 40.000 caracteres e a performance."""
    filler = "Buscamos alguém com muita vontade de aprender e evoluir com o time. "
    return f"{BACKEND_PYTHON_JOB}\n\n{filler * 500}"
