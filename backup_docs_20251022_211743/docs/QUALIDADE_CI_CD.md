# 🧪 Guia de Qualidade e CI/CD - Sistema SAP

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Testes](#testes)
- [CI/CD Pipeline](#cicd-pipeline)
- [Healthchecks](#healthchecks)
- [Comandos Make](#comandos-make)
- [Boas Práticas](#boas-práticas)

---

## 🎯 Visão Geral

A Fase 9 implementa automação completa de qualidade de código e CI/CD com:

- ✅ **Pre-commit hooks** - Validação antes de commit
- ✅ **Testes automatizados** - Coverage >= 80%
- ✅ **GitHub Actions** - Pipeline completa
- ✅ **Análise de segurança** - Bandit + pip-audit
- ✅ **Healthchecks** - Kubernetes-ready

### Ferramentas Utilizadas

| Ferramenta | Propósito | Quando Executa |
|------------|-----------|----------------|
| **Black** | Formatação de código | Pre-commit + CI |
| **isort** | Ordenação de imports | Pre-commit + CI |
| **Ruff** | Linter rápido | Pre-commit + CI |
| **MyPy** | Type checking | Pre-commit + CI |
| **Bandit** | Segurança | Pre-commit + CI |
| **Codespell** | Correção ortográfica | Pre-commit + CI |
| **Pytest** | Testes unitários | CI |
| **Coverage** | Cobertura de testes | CI |

---

## 🔧 Pre-commit Hooks

### Instalação

```bash
# 1. Instalar dependências
pip install -r requirements-dev.txt

# 2. Instalar hooks
pre-commit install

# 3. (Opcional) Executar em todos os arquivos
pre-commit run --all-files
```

### Hooks Configurados

#### 1. **Formatação**
- **Black**: Formatação automática (100 chars/linha)
- **isort**: Ordenação de imports (profile black)
- **Ruff**: Formatação adicional

#### 2. **Linting**
- **Ruff**: Linter moderno e rápido
  - Substitui flake8, pylint, pyupgrade
  - Correções automáticas quando possível

#### 3. **Segurança**
- **Bandit**: Detecta vulnerabilidades
- **detect-secrets**: Previne commit de credenciais

#### 4. **Type Checking**
- **MyPy**: Validação de type hints
  - Gradual typing (não estrito)

#### 5. **Qualidade Geral**
- **Codespell**: Correção ortográfica
- **Trailing whitespace**: Remove espaços
- **End of file**: Garante quebra de linha
- **Check YAML/JSON**: Valida sintaxe
- **Large files**: Previne commits > 500KB

### Uso

```bash
# Commit normal - hooks executam automaticamente
git add .
git commit -m "feat: adicionar feature X"

# Pular hooks (NÃO RECOMENDADO)
git commit --no-verify

# Executar hooks manualmente
pre-commit run --all-files

# Executar hook específico
pre-commit run black
pre-commit run ruff
```

---

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── __init__.py
├── auth/
│   ├── test_login.py
│   └── test_rbac.py
├── clientes/
│   ├── test_routes.py
│   ├── test_services.py
│   └── test_repositories.py
├── test_healthchecks.py       # FASE 9
├── test_contracts.py           # FASE 9
└── test_security.py
```

### Executar Testes

```bash
# Via Make (recomendado)
make test              # Com coverage
make test-fast         # Sem coverage (rápido)
make test-unit         # Apenas unitários
make test-integration  # Apenas integração

# Via Pytest direto
pytest                 # Todos os testes
pytest tests/auth/     # Diretório específico
pytest tests/test_healthchecks.py  # Arquivo específico
pytest -k "test_login" # Testes que contenham "login"
pytest -m unit         # Apenas marcados como unit
pytest -x              # Para no primeiro erro
```

### Coverage

**Meta**: >= 80% de cobertura

```bash
# Executar com coverage
pytest --cov=meu_app --cov-report=term-missing

# Gerar relatório HTML
pytest --cov=meu_app --cov-report=html
open htmlcov/index.html

# Coverage por módulo
pytest --cov=meu_app.pedidos
```

### Testes de Contrato (Snapshot)

Validam que formato de resposta não muda:

```python
def test_healthz_contract(client, snapshot):
    """Garante que /healthz não muda formato"""
    response = client.get('/healthz')
    data = response.get_json()
    data.pop('timestamp')
    
    assert data == snapshot  # Compara com snapshot salvo
```

**Atualizar snapshot**:
```bash
pytest --snapshot-update
```

---

## 🚀 CI/CD Pipeline

### GitHub Actions

**Arquivo**: `.github/workflows/ci.yml`

#### Jobs Configurados

1. **Lint** (5-10min)
   - Black (formatação)
   - isort (imports)
   - Ruff (linter)
   - MyPy (types)
   - Codespell (ortografia)

2. **Security** (5-10min)
   - Bandit (código)
   - pip-audit (dependências)
   - Gera relatórios JSON

3. **Test** (10-15min)
   - Matriz: Python 3.9, 3.10, 3.11
   - Pytest com coverage
   - Upload para Codecov
   - Artifacts de coverage

4. **Build** (2-5min)
   - Validação de imports
   - Gera relatórios CI

5. **Healthcheck** (1-2min)
   - Testa /healthz
   - Testa /readiness

### Triggers

- **Push** para `main` ou `develop`
- **Pull Requests** para `main` ou `develop`

### Artifacts Gerados

- `security-reports/` - Relatórios Bandit e pip-audit
- `coverage-report-py3.X/` - Coverage HTML
- `ci-reports/` - Relatórios gerais

### Status da Pipeline

```
✅ Lint      → Código formatado e sem erros
✅ Security  → Sem vulnerabilidades conhecidas
✅ Test      → Coverage >= 80%
✅ Build     → App inicializa sem erros
✅ Health    → Endpoints respondem
```

**CI vermelho = PR bloqueado** 🚫

---

## 🏥 Healthchecks

### Endpoints Implementados

#### `/healthz` - Liveness Probe

**Propósito**: Verificar se app está viva

**Uso**: Kubernetes restarta pod se retornar erro

```bash
curl http://localhost:5004/healthz
```

**Resposta**:
```json
{
  "status": "healthy",
  "service": "sistema-sap",
  "timestamp": "2025-10-08T00:00:00"
}
```

**Configuração Kubernetes**:
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 5004
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

#### `/readiness` - Readiness Probe

**Propósito**: Verificar se app está pronta para tráfego

**Uso**: Load balancer só roteia se retornar 200

```bash
curl http://localhost:5004/readiness
```

**Resposta**:
```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "cache": true
  },
  "timestamp": "2025-10-08T00:00:00"
}
```

**Configuração Kubernetes**:
```yaml
readinessProbe:
  httpGet:
    path: /readiness
    port: 5004
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2
```

---

## 🛠️ Comandos Make

O Makefile fornece atalhos para tarefas comuns:

### Desenvolvimento
```bash
make dev           # Iniciar servidor
make install       # Instalar dependências
make migrate       # Executar migrations
make init-db       # Inicializar banco
make backup-db     # Backup do banco
```

### Qualidade
```bash
make test          # Testes com coverage
make test-fast     # Testes rápidos
make lint          # Linters
make format        # Formatar código
make type-check    # Verificar tipos
make pre-commit    # Executar hooks
```

### Segurança
```bash
make security      # Análise completa
```

### Utilitários
```bash
make clean         # Limpar temporários
make status        # Ver status do sistema
make help          # Ver todos comandos
```

### CI Local
```bash
make ci-local      # Simular pipeline localmente
# Executa: format → lint → security → test
```

---

## 📚 Boas Práticas

### 1. Antes de Commitar

```bash
# Opção 1: Pre-commit (automático)
git add .
git commit -m "feat: minha feature"
# → Hooks executam automaticamente

# Opção 2: Manual
make format        # Formatar
make lint          # Validar
make test          # Testar
git add .
git commit -m "feat: minha feature"
```

### 2. Antes de Pull Request

```bash
# CI local completo
make ci-local

# Se tudo passar:
git push origin feature/minha-branch
# → Abrir PR no GitHub
```

### 3. Convenção de Commits

```bash
# Formato: <tipo>: <descrição>

feat: adicionar cache em vendedor dashboard
fix: corrigir erro de validação em pedidos
docs: atualizar guia de cache
test: adicionar testes de contrato
refactor: extrair lógica de apuração
perf: otimizar query de rankings
chore: atualizar dependências
```

### 4. Resolver Failures no CI

#### Lint Failed
```bash
# Executar localmente
make lint

# Corrigir automaticamente
make format

# Commit fixes
git add .
git commit -m "style: aplicar formatação"
```

#### Tests Failed
```bash
# Executar localmente
make test

# Ver detalhes
pytest -vv tests/caminho/test_arquivo.py

# Fix e commit
```

#### Security Failed
```bash
# Ver problemas
make security

# Resolver vulnerabilidades
pip install --upgrade <pacote>

# Ou ignorar se falso positivo
# Adicionar em pyproject.toml [tool.bandit] skips
```

---

## 📊 Métricas de Qualidade

### Coverage Mínimo

| Módulo | Coverage Mínimo | Atual |
|--------|-----------------|-------|
| **Repositories** | 90% | - |
| **Services** | 85% | - |
| **Routes** | 75% | - |
| **Models** | 80% | - |
| **TOTAL** | 80% | - |

### Performance SLA

| Endpoint | P95 Máximo | Atual |
|----------|------------|-------|
| Healthcheck | 100ms | - |
| Readiness | 500ms | - |
| APIs (GET) | 1000ms | - |

---

## 🚀 Deploy com CI/CD

### Workflow de Deploy

```
1. Developer cria branch
   └─ git checkout -b feature/nova-feature

2. Desenvolve e commita
   └─ Pre-commit valida código

3. Push para GitHub
   └─ git push origin feature/nova-feature

4. Abre Pull Request
   └─ GitHub Actions executa pipeline

5. CI Verde ✅
   ├─ Lint: Passed
   ├─ Security: Passed
   ├─ Tests: Passed (coverage 85%)
   ├─ Build: Passed
   └─ Health: Passed

6. Review e Merge
   └─ Merge para main

7. Deploy Automático (opcional)
   └─ Trigger deploy para produção
```

---

## ⚙️ Configuração Avançada

### pytest.ini (pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "--cov=meu_app",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=80"
]
markers = [
    "unit: testes unitários",
    "integration: testes de integração",
    "slow: testes lentos"
]
```

### Coverage

```toml
[tool.coverage.run]
branch = true
source = ["meu_app"]
omit = ["*/tests/*", "*/migrations/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:"
]
```

---

## 🐛 Troubleshooting

### Pre-commit muito lento

```bash
# Executar apenas em arquivos modificados
pre-commit run

# Pular hook específico
SKIP=mypy git commit -m "..."
```

### Testes falhando localmente mas passando no CI

```bash
# Limpar cache
make clean

# Reinstalar dependências
pip install -r requirements.txt -r requirements-dev.txt

# Executar novamente
make test
```

### CI falhando apenas em Python 3.11

```bash
# Testar localmente com pyenv
pyenv install 3.11
pyenv local 3.11
python -m venv venv311
source venv311/bin/activate
pip install -r requirements.txt
pytest
```

---

## 📚 Referências

- [Pre-commit Documentation](https://pre-commit.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Kubernetes Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

---

**Implementado por**: Sistema SAP - Fase 9  
**Data**: Outubro 2025  
**Versão**: 1.0

