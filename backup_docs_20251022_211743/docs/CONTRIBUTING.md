## Processo de Contribuição

Obrigado por contribuir! Para manter segurança e qualidade, siga as regras abaixo.

### 1. Fluxo de Trabalho (Git)
- Crie uma branch a partir de `main`/`master`.
- Abra um Pull Request (PR) descrevendo claramente a mudança.
- Pelo menos **1 revisão obrigatória** de outro desenvolvedor.
- Todos os checks do CI devem passar (lint, segurança, auditoria).

### 2. Padrões de Código
- Respeite o Flake8 (`.flake8`).
- Evite `except Exception:`; trate exceções específicas.
- Nomes claros e descritivos; evite abreviações obscuras.

### 3. Segurança
- Nunca commitar segredos. Use variáveis de ambiente.
- Execute `bandit` localmente antes do PR: `bandit -r . -x .venv,venv,instance`.
- Execute `pip-audit`: `pip-audit -r requirements.txt`.

### 4. Hooks de Pré-commit
Instale os hooks uma vez:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

Isso vai garantir execução de flake8 e bandit em cada commit.

### 5. Dependências
- Toda nova lib deve ser adicionada em `requirements.txt` (ou `requirements-dev.txt`).
- O Dependabot criará PRs semanais; revise e teste antes de aprovar.

### 6. Commits e PRs
- Mensagens de commit no imperativo, curtas e objetivas.
- Descreva impacto, risco e como testar no PR.

### 7. Testes Manuais Mínimos
- Rotas alteradas testadas localmente.
- Operações críticas (login, pedidos, apuração) exercitadas.

