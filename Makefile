# Makefile - Sistema GERPED
# =======================
# Comandos úteis para desenvolvimento
#
# Uso:
#   make help          - Mostra todos os comandos
#   make dev           - Inicia servidor de desenvolvimento
#   make test          - Executa testes
#   make lint          - Executa linters
#   make format        - Formata código
#
# Autor: Sistema GERPED - Fase 9

.PHONY: help dev test lint format clean install migrate security restart server-start server-stop server-status server-logs

# Variáveis
PYTHON := python3
VENV := venv
FLASK := flask
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

# Cores para output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help:
	@echo "$(BLUE)Sistema GERPED - Comandos Disponíveis$(NC)"
	@echo ""
	@echo "$(GREEN)Desenvolvimento:$(NC)"
	@echo "  make dev              - Inicia servidor de desenvolvimento"
	@echo "  make server-start     - Inicia servidor (com gerenciamento)"
	@echo "  make server-stop      - Para servidor"
	@echo "  make restart          - Reinicia servidor"
	@echo "  make server-status    - Status do servidor"
	@echo "  make server-logs      - Mostra logs em tempo real"
	@echo "  make install          - Instala dependências"
	@echo "  make migrate          - Executa migrations"
	@echo "  make run-worker       - Inicia worker assíncrono (Celery/RQ)"
	@echo ""
	@echo "$(GREEN)Qualidade:$(NC)"
	@echo "  make test             - Executa testes com coverage"
	@echo "  make test-fast        - Executa testes sem coverage"
	@echo "  make lint             - Executa linters"
	@echo "  make format           - Formata código (black + isort)"
	@echo "  make type-check       - Verifica tipos (mypy)"
	@echo "  make pre-commit       - Executa pre-commit hooks"
	@echo "  make smoke            - Smoke tests (endpoints críticos)"
	@echo ""
	@echo "$(GREEN)Segurança:$(NC)"
	@echo "  make security         - Análise de segurança (bandit + pip-audit)"
	@echo ""
	@echo "$(GREEN)Utilitários:$(NC)"
	@echo "  make clean            - Remove arquivos temporários"
	@echo "  make init-db          - Inicializa banco de dados"
	@echo "  make backup-db        - Faz backup do banco"
	@echo "  make docs             - Abre documentação"

# ===========================
# DESENVOLVIMENTO
# ===========================

dev:
	@echo "$(GREEN)🚀 Iniciando servidor de desenvolvimento...$(NC)"
	@bash scripts/manage_server.sh start

server-start:
	@bash scripts/manage_server.sh start

server-stop:
	@bash scripts/manage_server.sh stop

restart:
	@echo "$(GREEN)♻️  Reiniciando servidores...$(NC)"
	@$(MAKE) server-stop || true
	@sleep 1
	@$(MAKE) server-start
	
server-status:
	@bash scripts/manage_server.sh status

server-logs:
	@bash scripts/manage_server.sh logs

run-worker:
	@echo "$(GREEN)🔄 Iniciando worker RQ (Fase 7)...$(NC)"
	@echo "$(BLUE)ℹ️  Processando fila 'ocr' com timeout de 5 minutos$(NC)"
	@echo "$(YELLOW)⚠️  Certifique-se que o Redis está rodando: redis-server$(NC)"
	@echo ""
	$(PYTHON) worker.py

install:
	@echo "$(GREEN)📦 Instalando dependências...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt

install-prod:
	@echo "$(GREEN)📦 Instalando dependências de produção...$(NC)"
	$(PIP) install -r requirements.txt

migrate:
	@echo "$(GREEN)🗃️ Executando migrations...$(NC)"
	$(PYTHON) alembic_migrate.py db upgrade || $(FLASK) db upgrade

migrate-create:
	@echo "$(YELLOW)🗃️ Criando nova migration...$(NC)"
	@read -p "Descrição da migration: " desc; \
	$(PYTHON) alembic_migrate.py db migrate -m "$$desc" || $(FLASK) db migrate -m "$$desc"

init-db:
	@echo "$(GREEN)🗃️ Inicializando banco de dados...$(NC)"
	$(PYTHON) init_db.py

backup-db:
	@echo "$(GREEN)💾 Fazendo backup do banco...$(NC)"
	cp instance/sistema.db instance/backups/sistema_backup_$(shell date +%Y%m%d_%H%M%S).db
	@echo "$(GREEN)✅ Backup criado em instance/backups/$(NC)"

backup-financeiro:
	@echo "$(GREEN)💾 Criando backup completo (banco + recibos)...$(NC)"
	@chmod +x scripts/backup_financeiro.sh
	@scripts/backup_financeiro.sh
	@echo "$(GREEN)✅ Backup salvo em backups/<timestamp>$(NC)"

# ===========================
# TESTES
# ===========================

test:
	@echo "$(GREEN)🧪 Executando testes com coverage...$(NC)"
	$(PYTEST) --cov=meu_app --cov-report=term-missing --cov-report=html

test-fast:
	@echo "$(GREEN)⚡ Executando testes (sem coverage)...$(NC)"
	$(PYTEST) -x --tb=short

test-unit:
	@echo "$(GREEN)🧪 Executando testes unitários...$(NC)"
	$(PYTEST) -m unit

test-integration:
	@echo "$(GREEN)🧪 Executando testes de integração...$(NC)"
	$(PYTEST) -m integration

test-verbose:
	@echo "$(GREEN)🧪 Executando testes (verbose)...$(NC)"
	$(PYTEST) -vv

coverage-report:
	@echo "$(GREEN)📊 Abrindo relatório de coverage...$(NC)"
	open htmlcov/index.html || xdg-open htmlcov/index.html

smoke:
	@echo "$(GREEN)🧪 Executando smoke tests...$(NC)"
	@chmod +x scripts/smoke_test.sh
	@./scripts/smoke_test.sh

# ===========================
# QUALIDADE DE CÓDIGO
# ===========================

lint:
	@echo "$(GREEN)🔍 Executando linters...$(NC)"
	@echo "$(BLUE)→ Ruff$(NC)"
	ruff check meu_app tests
	@echo "$(BLUE)→ pydocstyle$(NC)"
	pydocstyle meu_app

format:
	@echo "$(GREEN)✨ Formatando código...$(NC)"
	@echo "$(BLUE)→ Black$(NC)"
	black meu_app tests
	@echo "$(BLUE)→ isort$(NC)"
	isort meu_app tests

type-check:
	@echo "$(GREEN)🔤 Verificando tipos...$(NC)"
	mypy meu_app --ignore-missing-imports

pre-commit:
	@echo "$(GREEN)🔧 Executando pre-commit hooks...$(NC)"
	pre-commit run --all-files

pre-commit-install:
	@echo "$(GREEN)🔧 Instalando pre-commit hooks...$(NC)"
	pre-commit install

# ===========================
# SEGURANÇA
# ===========================

security:
	@echo "$(GREEN)🔒 Executando análise de segurança...$(NC)"
	@echo "$(BLUE)→ Bandit$(NC)"
	bandit -r meu_app -f txt
	@echo ""
	@echo "$(BLUE)→ pip-audit$(NC)"
	pip-audit || true

# ===========================
# LIMPEZA
# ===========================

clean:
	@echo "$(GREEN)🧹 Limpando arquivos temporários...$(NC)"
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + || true
	find . -type d -name '.ruff_cache' -exec rm -rf {} + || true
	rm -rf htmlcov/
	rm -f .coverage
	rm -f coverage.xml
	@echo "$(GREEN)✅ Limpeza concluída$(NC)"

clean-all: clean
	@echo "$(YELLOW)🧹 Limpando cache e builds...$(NC)"
	rm -rf $(VENV)
	rm -rf node_modules
	@echo "$(GREEN)✅ Limpeza completa concluída$(NC)"

# ===========================
# CI/CD LOCAL
# ===========================

ci-local:
	@echo "$(GREEN)🚀 Executando CI/CD local...$(NC)"
	@echo ""
	@echo "$(BLUE)1/4 - Formatação$(NC)"
	@make format
	@echo ""
	@echo "$(BLUE)2/4 - Linting$(NC)"
	@make lint
	@echo ""
	@echo "$(BLUE)3/4 - Segurança$(NC)"
	@make security
	@echo ""
	@echo "$(BLUE)4/4 - Testes$(NC)"
	@make test
	@echo ""
	@echo "$(GREEN)✅ CI/CD local completo!$(NC)"

# ===========================
# DOCUMENTAÇÃO
# ===========================

docs:
	@echo "$(GREEN)📚 Documentação disponível:$(NC)"
	@echo "  - docs/README.md"
	@echo "  - docs/GUIA_DESENVOLVEDOR.md"
	@echo "  - docs/GUIA_USUARIO.md"
	@echo "  - docs/MIGRATIONS_ALEMBIC.md (FASE 5)"
	@echo "  - docs/OBSERVABILIDADE.md (FASE 6)"
	@echo "  - docs/FASE7_FILA_ASSINCRONA.md (FASE 7)"
	@echo "  - docs/GUIA_CACHE.md (FASE 8)"
	@echo "  - docs/QUALIDADE_CI_CD.md (FASE 9)"
	@echo "  - docs/API_EXAMPLES.md (FASE 10)"
	@echo "  - docs/NEON_SETUP.md"
	@echo "  - docs/SECURITY_PIPELINE.md"
	@echo "  - docs/GO_LIVE_CHECKLIST.md"
	@echo "  - RECOMENDACOES_INDICES.md (FASE 8)"
	@echo ""
	@echo "$(BLUE)🌐 Documentação interativa:$(NC)"
	@echo "  http://localhost:5004/docs (Swagger UI)"

docs-open:
	@echo "$(GREEN)🌐 Abrindo documentação interativa...$(NC)"
	@open http://localhost:5004/docs || xdg-open http://localhost:5004/docs

# ===========================
# DIAGNÓSTICO
# ===========================

status:
	@echo "$(GREEN)📊 Status do Sistema$(NC)"
	@echo ""
	@echo "$(BLUE)Python:$(NC) $(shell $(PYTHON) --version)"
	@echo "$(BLUE)Ambiente Virtual:$(NC) $(shell [ -d $(VENV) ] && echo '✅ Ativo' || echo '❌ Não encontrado')"
	@echo "$(BLUE)Banco de Dados:$(NC) $(shell [ -f instance/sistema.db ] && echo '✅ Existe' || echo '❌ Não encontrado')"
	@echo "$(BLUE)Redis:$(NC) $(shell redis-cli ping 2>/dev/null || echo '❌ Não disponível')"
	@echo ""
	@echo "$(BLUE)Migrations:$(NC)"
	@$(PYTHON) alembic_migrate.py db current 2>/dev/null || echo "  Nenhuma migration aplicada"
