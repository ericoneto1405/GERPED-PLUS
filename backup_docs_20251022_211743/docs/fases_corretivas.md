🧭 Fase 0 — Discovery e Mapa de Risco

Ferramenta: ✅ GEMINI CLI (melhor para diagnóstico e leitura contextual)

Contexto: Repositório Flask "sistema-sap".
Meta: Fazer descoberta técnica e mapa de risco em 1 passada.

Tarefas:
1) Gerar árvore resumida do repo (até 3 níveis) e identificar:
   - Ponto de entrada Flask (run.py/wsgi/app factory)
   - Blueprints, models, services, templates, static, migrations
   - Arquivos de config (.env, config.py)
   - Testes e CI
2) Checar riscos objetivos:
   - Credenciais default no README / seeds
   - Ausência de CSRF/Talisman/headers de segurança
   - Falta de RBAC / autorização por escopo
   - Falta de Alembic/migrations coerentes
   - Uso de SQLite em produção
   - Uploads sem validação (OCR)
3) Emitir relatório em markdown com 3 seções:
   A) Arquitetura atual  
   B) Riscos (Crítico/Alto/Médio/Baixo)  
   C) Quick wins (< 2 h)

Saída esperada: `RELATORIO_DISCOVERY.md`

⚙️ Fase 1 — Config e App Factory

Ferramenta: ✅ CURSOR IDE (modo agente) (edição de múltiplos arquivos + lint automático)

Contexto: Migrar para padrão Flask App Factory + config por ambiente.

Tarefas:
1) Criar app/__init__.py com create_app(config_class)
2) Criar config.py com classes Dev/Test/Prod
3) Criar wsgi.py e ajustar run.py
4) Gerar .env.example completo
Critérios:
- App roda via flask run e Gunicorn
- Lint e imports OK
Saída:
- app/__init__.py
- config.py
- wsgi.py
- .env.example

🛡️ Fase 2 — Segurança Base

Ferramenta: ✅ CODEX CLI (execução precisa e scripts de segurança automatizáveis)

Contexto: Aplicar segurança base no Flask.

Tarefas:
1) Adicionar Flask-WTF CSRF global
2) Headers: X-Frame-Options, CSP, etc. (via Flask-Talisman)
3) Cookies de sessão seguros
4) Rate-limit em /login
5) Remover credenciais default
Saída:
- app/security.py
- ajustes em templates
- tests/test_security.py

🔐 Fase 3 — RBAC e Autorização

Ferramenta: ✅ CURSOR IDE (modo agente)

Contexto: Implementar papéis/escopos (ADMIN, FINANCEIRO, VENDEDOR, LOGISTICA).

Tarefas:
1) Criar decorator @requires_roles
2) Mapear rotas por papel
3) Template 403 amigável
4) Testes de acesso permitido/negado
Saída:
- app/auth/rbac.py
- tests/test_rbac.py

🧩 Fase 4 — Services, Repositories e Schemas

Ferramenta: ✅ CURSOR IDE (modo agente)

Contexto: Introduzir camadas limpas.

Tarefas:
1) Criar app/<dominio>/{routes,services,repositories,schemas}.py
2) Mover regra de negócio para services
3) Validar entrada/saída via Pydantic/Marshmallow
4) Garantir testes unitários independentes do app context

🗃️ Fase 5 — Banco e Migrations

Ferramenta: ✅ CODEX CLI

Contexto: Configurar Alembic e banco.

Tarefas:
1) Configurar Alembic (alembic.ini, env.py, versions/)
2) Autogenerate inicial
3) Scripts upgrade/downgrade
4) Postgres (prod) + SQLite (dev)
5) Seeds seguros

📊 Fase 6 — Observabilidade e Logs

Ferramenta: ✅ GEMINI CLI

Contexto: Instrumentar logs e métricas.

Tarefas:
1) Log estruturado JSON com request_id
2) Métricas Prometheus/OpenTelemetry
3) Middleware de logging
Saída:
- app/obs/logging.py
- app/obs/metrics.py

⚙️ Fase 7 — Fila Assíncrona (OCR / PDF / Uploads)

Ferramenta: ✅ CURSOR IDE (modo agente)

Contexto: Offload de tarefas pesadas e uploads seguros.

Tarefas:
1) Integrar RQ/Celery
2) Validar MIME/extensão/tamanho
3) Salvar fora do webroot
4) Hash + nome aleatório
5) Endpoints de status de job

🚀 Fase 8 — Cache e Performance

Ferramenta: ✅ CODEX CLI

Contexto: Cache e performance.

Tarefas:
1) Integrar Flask-Caching (Redis)
2) Cachear endpoints de leitura pesada
3) Invalidação por evento
4) Gerar RECOMENDACOES_INDICES.md

🧪 Fase 9 — Qualidade, Testes e CI/CD

Ferramenta: ✅ GEMINI CLI

Contexto: Padronizar qualidade e automação.

Tarefas:
1) Pre-commit: black, ruff, isort, bandit, mypy
2) Pytest com coverage
3) GitHub Actions (lint, segurança, testes)
4) Healthchecks /healthz e /readiness

📖 Fase 10 — Documentação e Developer Experience

Ferramenta: ✅ CURSOR IDE (modo agente)

Contexto: Documentar APIs e onboarding.

Tarefas:
1) OpenAPI com flask-smorest + /docs
2) Exemplos de requisições
3) Makefile (dev, test, lint, migrate, run-worker)
4) Atualizar README e fluxos

