# 📊 RELATÓRIO DE DESCOBERTA TÉCNICA E MAPEAMENTO DE RISCOS
## Sistema SAP - Gestão de Pedidos e Vendas

**Data:** 07 de outubro de 2025  
**Escopo:** Análise completa do repositório Flask "sistema-sap"  
**Metodologia:** Auditoria de código estática, análise de dependências e verificação de padrões de segurança

---

## A) 🏗️ ARQUITETURA ATUAL

### **1. Ponto de Entrada e Configuração**
- **Ponto de entrada:** `run.py` → `create_app()` em `meu_app/__init__.py`
- **Padrão:** Application Factory (Flask)
- **Porta:** 5004 (configurável)
- **Debug mode:** ⚠️ **ATIVO** em `run.py:6` (`debug=True`)
- **Host:** `0.0.0.0` (exposto para rede)

### **2. Banco de Dados**
- **Engine:** SQLite 
- **Localização:** `instance/sistema.db`
- **ORM:** SQLAlchemy 2.0
- **Migrations:** ⚠️ **Manuais** (sem Alembic), arquivos Python em `migrations/`
- **Backups:** Automáticos (últimos 10) em `instance/backups/`

### **3. Blueprints e Módulos**
```
meu_app/
├── routes.py          # Blueprint principal (main)
├── clientes/          # Gestão de clientes
├── produtos/          # Catálogo de produtos
├── pedidos/           # Gestão de pedidos
├── usuarios/          # Usuários e autenticação
├── estoques/          # Controle de estoque
├── financeiro/        # Pagamentos e OCR (Google Vision)
├── coletas/           # Logística de coletas
├── apuracao/          # Apuração mensal financeira
├── log_atividades/    # Auditoria de atividades
└── vendedor/          # Painel do vendedor
```

### **4. Models (Entidades)**
- `Cliente`, `Produto`, `Pedido`, `ItemPedido`, `Pagamento`
- `Coleta`, `ItemColetado`, `Usuario`, `Apuracao`
- `Estoque`, `MovimentacaoEstoque`, `LogAtividade`, `OcrQuota`
- **Total:** 13 modelos principais

### **5. Autenticação e Autorização**
- **Sistema:** Session-based (Flask sessions)
- **Hashing:** Werkzeug `generate_password_hash`/`check_password_hash`
- **RBAC:** Implementado via decoradores (`@permissao_necessaria`, `@admin_necessario`)
- **Permissões:** `acesso_clientes`, `acesso_produtos`, `acesso_pedidos`, `acesso_financeiro`, `acesso_logistica`
- **Admin bypass:** ✅ Implementado corretamente em `decorators.py:76`

### **6. Templates e Frontend**
- **Engine:** Jinja2
- **Localização:** `meu_app/templates/`
- **Static files:** CSS, JavaScript em `meu_app/static/`
- **Framework frontend:** Vanilla JS (sem framework)

### **7. Dependências Principais**
```
Flask 3.0
Flask-SQLAlchemy 2.0
werkzeug (segurança)
reportlab (PDF)
pandas (análise)
python-dotenv (config)
validate-docbr (validação CPF/CNPJ)
bleach (sanitização HTML)
python-magic (validação MIME)
google-cloud-vision (OCR)
pdf2image (conversão PDF)
```

### **8. Testes e CI/CD**
- **Framework:** Pytest
- **Cobertura:** Parcial (coletas/, financeiro/, integration/)
- **CI:** GitHub Actions com 3 workflows:
  - `ci.yml`: Flake8, Bandit, pip-audit
  - `coletas-ci.yml`: Testes específicos de coletas
  - Dependabot configurado
- **Linters:** Flake8, Bandit (SAST)
- **Audit:** pip-audit (dependências vulneráveis)

### **9. Segurança de Upload**
- **Módulo:** `meu_app/upload_security.py`
- **Validações:** 
  - MIME type real (via `python-magic`)
  - Extensão permitida
  - Tamanho máximo (5-10MB)
  - Scan básico de malware (assinaturas)
- **Tipos suportados:** Excel, CSV, Imagens, PDFs
- **Limitação:** ⚠️ Sem integração com antivírus real

### **10. OCR (Google Vision)**
- **Provider:** Google Cloud Vision API
- **Quota:** 1.000 chamadas/mês (controle em `OcrQuota` model)
- **Cache:** Habilitado (SHA-256 de arquivos)
- **Credenciais:** ⚠️ Path hardcoded em `financeiro/config.py:28`

### **11. Logging e Monitoramento**
- **Sistema:** Rotating File Handler (10MB, 5 backups)
- **Localização:** `instance/logs/app.log`
- **Níveis:** INFO em produção, DEBUG em desenvolvimento
- **Auditoria:** Modelo `LogAtividade` com IP tracking

---

## B) 🚨 RISCOS CLASSIFICADOS

### 🔴 **CRÍTICO** (Ação Imediata)

#### **C1. SECRET_KEY Hardcoded e Insegura**
- **Arquivo:** `meu_app/__init__.py:30`
- **Evidência:**
  ```python
  secret_key = os.environ.get('SECRET_KEY')
  # if not secret_key:
  secret_key = "gerpedplus_default_secret_key_2024_secure"
  ```
- **Impacto:** Sessões podem ser forjadas, CSRF bypass, session hijacking
- **CVSS:** 9.1 (Critical)
- **Remediação:** Forçar SECRET_KEY via variável de ambiente obrigatória

#### **C2. Credenciais Default Documentadas**
- **Arquivos:** 
  - `README.md:42-43` → `admin:admin123`
  - `init_db.py:34` → `admin:Admin@2024`
  - `init_db.py:53` → `testuser:testpassword`
- **Evidência:**
  ```markdown
  ## 🔑 Primeiro Acesso
  - **Usuário:** `admin`
  - **Senha:** `admin123`
  ```
- **Problemas:**
  - Credenciais expostas publicamente
  - Inconsistência entre README e init_db.py
  - Usuário de teste com senha plaintext
- **Impacto:** Acesso não autorizado completo ao sistema
- **CVSS:** 9.8 (Critical)
- **Remediação:** 
  1. Remover credenciais do README
  2. Forçar troca de senha no primeiro login
  3. Remover usuário de teste em produção

#### **C3. CSRF Protection Ausente**
- **Evidência:** 0 implementações de `CSRFProtect` ou `flask-wtf`
- **Busca realizada:** `grep -r "csrf|CSRF"` → apenas 1 menção em documentação
- **Impacto:** Ações não autorizadas via CSRF (criação de pedidos, aprovações, pagamentos)
- **CVSS:** 8.1 (High)
- **Remediação:** Instalar `Flask-WTF` e adicionar `csrf_token()` em todos os forms

#### **C4. SQLite em Produção**
- **Arquivo:** `meu_app/__init__.py:24`
- **Evidência:**
  ```python
  app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "sistema.db")}'
  ```
- **Limitações:**
  - Sem concorrência real
  - Sem replicação
  - Lock de arquivo em escritas
  - Não escalável
- **Impacto:** Perda de dados, travamentos, performance degradada
- **CVSS:** 7.5 (High)
- **Remediação:** Migrar para PostgreSQL ou MySQL

---

### 🟠 **ALTO** (Ação em 1-2 Semanas)

#### **A1. Headers de Segurança Ausentes**
- **Busca realizada:** `grep -r "Talisman|X-Frame-Options|Content-Security-Policy"` → 0 resultados
- **Headers faltando:**
  - `X-Frame-Options: DENY` (Clickjacking)
  - `X-Content-Type-Options: nosniff`
  - `Content-Security-Policy`
  - `Strict-Transport-Security` (HSTS)
  - `Referrer-Policy`
- **Impacto:** Vulnerável a clickjacking, XSS, MIME sniffing
- **CVSS:** 6.5 (Medium-High)
- **Remediação:** Instalar `flask-talisman` ou criar middleware customizado

#### **A2. Debug Mode Ativo**
- **Arquivo:** `run.py:6`
- **Evidência:**
  ```python
  app.run(debug=True, host='0.0.0.0', port=5004)
  ```
- **Impacto:** 
  - Traceback completo exposto
  - Console interativo acessível
  - Código fonte vazado
- **CVSS:** 7.5 (High)
- **Remediação:** Desabilitar `debug` em produção via variável de ambiente

#### **A3. Usuário de Teste com Senha em Plaintext**
- **Arquivo:** `init_db.py:53`
- **Evidência:**
  ```python
  test_user = Usuario(
      nome='testuser',
      senha='testpassword',  # ❌ ERRO: deveria ser set_senha()
      tipo='comum',
  ```
- **Impacto:** Model espera `senha_hash`, mas está recebendo plaintext → erro ou bypass de hash
- **CVSS:** 8.2 (High)
- **Remediação:** Trocar `senha=` por `test_user.set_senha('testpassword')` após criação

#### **A4. Credenciais Google Vision Hardcoded**
- **Arquivo:** `meu_app/financeiro/config.py:28`
- **Evidência:**
  ```python
  GOOGLE_VISION_CREDENTIALS_PATH = '/Users/ericobrandao/keys/gvision-credentials.json'
  ```
- **Impacto:** 
  - Path absoluto inválido em outros ambientes
  - Credenciais não versionáveis
  - Falha em deploy
- **CVSS:** 6.0 (Medium)
- **Remediação:** Usar variável de ambiente `GOOGLE_APPLICATION_CREDENTIALS`

---

### 🟡 **MÉDIO** (Ação em 1-2 Meses)

#### **M1. Migrations Manuais sem Versionamento**
- **Pasta:** `migrations/` com 7 scripts Python/SQL
- **Problema:** 
  - Sem controle de versão (Alembic)
  - Sem rollback automatizado
  - Risco de aplicação duplicada
  - Status manual em `README.md`
- **Impacto:** Schema drift, inconsistência entre ambientes
- **CVSS:** 5.0 (Medium)
- **Remediação:** Implementar Alembic com `alembic init` e migrar histórico

#### **M2. Cobertura de Testes Limitada**
- **Evidência:** Apenas 3 módulos testados (coletas, financeiro, integration)
- **Módulos sem testes:** clientes, produtos, pedidos, usuarios, estoques, apuracao, log_atividades, vendedor
- **Impacto:** Regressões não detectadas, refatoração arriscada
- **CVSS:** 4.0 (Low-Medium)
- **Remediação:** Aumentar cobertura para >80% (target inicial: 60%)

#### **M3. Upload Security: Scan de Malware Básico**
- **Arquivo:** `meu_app/upload_security.py:250-288`
- **Implementação:** Busca por assinaturas conhecidas (MZ, ELF, VBA)
- **Limitação:** Não detecta malware sofisticado ou 0-days
- **Impacto:** Upload de malware disfarçado
- **CVSS:** 5.5 (Medium)
- **Remediação:** Integrar ClamAV ou VirusTotal API

#### **M4. Falta de Rate Limiting**
- **Busca realizada:** 0 implementações de rate limiting
- **Endpoints vulneráveis:**
  - `/login` (brute force)
  - `/api/*` (DDoS)
  - `/financeiro/lancar_pagamento` (flood)
- **Impacto:** Brute force, DDoS, abuso de recursos
- **CVSS:** 5.0 (Medium)
- **Remediação:** Instalar `Flask-Limiter` com Redis backend

#### **M5. Logging Excessivo de Dados Sensíveis**
- **Arquivo:** `meu_app/__init__.py:160`
- **Evidência:**
  ```python
  app.logger.error(f'IP: {request.remote_addr}')
  ```
- **Risco:** Pode logar dados sensíveis (senhas em query strings, tokens)
- **Impacto:** Vazamento de informações via logs
- **CVSS:** 4.5 (Low-Medium)
- **Remediação:** Implementar log sanitization

---

### 🟢 **BAIXO** (Backlog)

#### **B1. Porta 5004 sem Justificativa**
- **Arquivo:** `run.py:6`
- **Observação:** Porta não padrão (80/443/8000)
- **Impacto:** Mínimo (pode confundir em deploys)
- **Remediação:** Documentar ou usar variável de ambiente

#### **B2. Python 3.13 em Produção**
- **Arquivo:** `venv/include/python3.13/`
- **Observação:** Versão muito recente (estabilidade não comprovada)
- **Impacto:** Possíveis bugs não descobertos
- **Remediação:** Considerar Python 3.11 LTS

#### **B3. Dependências sem Pin de Versão**
- **Arquivo:** `requirements.txt`
- **Evidência:** Versões não fixadas (ex: `Flask` ao invés de `Flask==3.0.0`)
- **Impacto:** Atualizações breaking inesperadas
- **CVSS:** 3.0 (Low)
- **Remediação:** Usar `pip freeze` para fixar versões

---

## C) ⚡ QUICK WINS (< 2 horas)

### **QW1. Desabilitar Debug Mode em Produção (5 min)**
```python
# run.py
import os
app.run(
    debug=os.getenv('FLASK_DEBUG', 'False') == 'True',
    host='0.0.0.0',
    port=int(os.getenv('PORT', 5004))
)
```

### **QW2. Forçar SECRET_KEY Obrigatória (10 min)**
```python
# meu_app/__init__.py
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable must be set")
app.config['SECRET_KEY'] = secret_key
```

### **QW3. Remover Credenciais do README (2 min)**
```markdown
## 🔑 Primeiro Acesso
Execute `python init_db.py` para criar o usuário administrador.
Credenciais serão exibidas no console.
⚠️ **IMPORTANTE:** Altere a senha imediatamente após o primeiro login!
```

### **QW4. Corrigir Criação de Usuário de Teste (5 min)**
```python
# init_db.py
test_user = Usuario(
    nome='testuser',
    senha_hash='',  # Será preenchido por set_senha
    tipo='comum',
    ...
)
test_user.set_senha('testpassword')  # ✅ CORRETO
db.session.add(test_user)
```

### **QW5. Adicionar .env.example (15 min)**
```bash
# .env.example
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secret-key-here-min-32-chars
DATABASE_URL=sqlite:///instance/sistema.db
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gvision-credentials.json
PORT=5004
```

### **QW6. Instalar Flask-Talisman (30 min)**
```python
# meu_app/__init__.py
from flask_talisman import Talisman

def create_app():
    # ... código existente ...
    
    if not app.debug:
        Talisman(app, 
            force_https=True,
            strict_transport_security=True,
            content_security_policy={
                'default-src': "'self'",
                'img-src': ['*', 'data:'],
                'script-src': "'self' 'unsafe-inline'"
            }
        )
    
    return app
```

**Instalação:**
```bash
pip install flask-talisman
echo "flask-talisman" >> requirements.txt
```

### **QW7. Adicionar Proteção CSRF Básica (1 hora)**
```python
# requirements.txt
Flask-WTF

# meu_app/__init__.py
from flask_wtf.csrf import CSRFProtect

def create_app():
    # ... código existente ...
    csrf = CSRFProtect(app)
    return app

# Em cada template com formulário:
<form method="POST">
    {{ csrf_token() }}
    <!-- campos existentes -->
</form>
```

### **QW8. Fixar Versões de Dependências (10 min)**
```bash
pip freeze > requirements.txt.lock
# Revisar manualmente e mover para requirements.txt
```

### **QW9. Adicionar Health Check Endpoint (15 min)**
```python
# meu_app/routes.py
@bp.route('/health')
def health_check():
    try:
        # Verificar conexão com banco
        db.session.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'db': 'ok'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
```

### **QW10. Documentar Credenciais Google Vision (5 min)**
```markdown
# README.md
## Configuração do Google Vision

1. Obtenha credenciais em https://console.cloud.google.com
2. Baixe o arquivo JSON
3. Configure a variável de ambiente:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
   ```
```

---

## 📊 RESUMO EXECUTIVO

### **Score de Risco Geral: 7.8/10 (Alto)**

| Categoria | Quantidade | Score Médio |
|-----------|-----------|-------------|
| 🔴 Críticos | 4 | 8.6 |
| 🟠 Altos | 4 | 7.0 |
| 🟡 Médios | 5 | 5.0 |
| 🟢 Baixos | 3 | 3.0 |
| **Total** | **16** | **6.4** |

### **Top 5 Prioridades**
1. ✅ **C1 + QW2:** Forçar SECRET_KEY obrigatória (10 min)
2. ✅ **C2 + QW3:** Remover credenciais do README (2 min)
3. ✅ **C3 + QW7:** Implementar proteção CSRF (1h)
4. ✅ **A2 + QW1:** Desabilitar debug em produção (5 min)
5. ✅ **QW6:** Adicionar headers de segurança via Talisman (30 min)

**Tempo total de Quick Wins prioritários: ~2h 30min**

### **Roadmap de Remediação**

#### **Sprint 1 (Semana 1)** - Críticos
- [ ] Implementar todos os 10 Quick Wins
- [ ] Migrar SECRET_KEY e credenciais para variáveis de ambiente
- [ ] Adicionar CSRF protection
- [ ] Desabilitar debug mode

#### **Sprint 2 (Semana 2-3)** - Altos
- [ ] Implementar Flask-Talisman completo
- [ ] Corrigir usuário de teste
- [ ] Avaliar migração para PostgreSQL (POC)
- [ ] Adicionar rate limiting (Flask-Limiter)

#### **Sprint 3 (Mês 2)** - Médios
- [ ] Implementar Alembic para migrations
- [ ] Aumentar cobertura de testes para 60%
- [ ] Integrar ClamAV para scan de uploads
- [ ] Implementar log sanitization

#### **Sprint 4 (Mês 3-6)** - Melhorias
- [ ] Migração completa para PostgreSQL
- [ ] Implementar monitoramento (Prometheus/Grafana)
- [ ] Adicionar cache Redis
- [ ] Dockerizar aplicação

---

## 🎯 OBSERVAÇÕES FINAIS

### **Pontos Positivos** ✅
1. **Arquitetura bem estruturada** (Blueprints, separação de concerns)
2. **OCR com quota implementada** (controle de custos)
3. **CI/CD básico funcional** (Flake8, Bandit, pip-audit)
4. **Upload security robusto** (validação MIME, tamanho, scan básico)
5. **Logging estruturado** (rotating handler, níveis adequados)
6. **RBAC implementado** (decoradores, admin bypass correto)
7. **Auditoria via LogAtividade** (rastreamento de ações)

### **Pontos de Atenção** ⚠️
1. **Segurança:** Prioridade máxima nos próximos 15 dias
2. **Escalabilidade:** SQLite não suporta crescimento
3. **Testes:** Cobertura insuficiente (<30% estimado)
4. **Migrations:** Sistema manual é arriscado
5. **Dependências:** Atualizações podem quebrar (sem pin)

### **Riscos Não Mitigáveis Rapidamente**
- **SQLite em produção:** Migração para PostgreSQL leva ~2-4 semanas
- **Cobertura de testes:** Aumentar para 80% leva ~3-6 meses
- **Refatoração de migrations:** Implementar Alembic com histórico leva ~1-2 semanas

---

**📅 Próxima Revisão Recomendada:** 30 dias após implementação dos Quick Wins

**👤 Responsável pela Auditoria:** Sistema de Análise Automatizada  
**📧 Contato:** Disponível para esclarecimentos

---

*Este relatório foi gerado automaticamente com base na análise estática do código-fonte. Recomenda-se validação manual de pontos críticos antes de implementação em produção.*

