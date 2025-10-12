# 🎯 PLANO DE AÇÃO: Reduzir Risco de MÉDIO para BAIXO

## 📊 Status Atual → Meta

**Atual:** 🟡 RISCO MÉDIO  
**Meta:** 🟢 RISCO BAIXO  
**Tempo Estimado:** 2-3 horas  
**Dificuldade:** ⭐⭐⭐ Média

---

## 🚨 Vulnerabilidades a Corrigir (17 total)

### Prioridade por Impacto:

| Prioridade | Vulnerabilidade | Quantidade | Tempo |
|------------|----------------|------------|-------|
| 🔴 **ALTA** | Token Hardcoded | 1 | 30 min |
| 🟡 **MÉDIA** | CSRF Token Missing | 10 | 1-2h |
| 🔵 **BAIXA** | XSS Potencial | 2 | 15 min |

---

## 🔴 ALTA PRIORIDADE

### 1. Remover Token CSP Hardcoded

**Vulnerabilidade:** Token CSP hardcoded em `base.html`

#### 📍 Localização:
```html
<!-- meu_app/templates/base.html:9 -->
<meta http-equiv="Content-Security-Policy" content="..." nonce="hardcoded_token">
```

#### ✅ Solução:

**Passo 1:** Modificar `meu_app/__init__.py`

```python
# Adicionar após criar o app Flask
import secrets
from flask import g

@app.before_request
def generate_nonce():
    """Gera um nonce único para cada request"""
    g.nonce = secrets.token_urlsafe(16)

@app.context_processor
def inject_nonce():
    """Injeta o nonce em todos os templates"""
    return dict(nonce=getattr(g, 'nonce', ''))
```

**Passo 2:** Verificar `base.html`

```html
<!-- Deve estar assim (já correto): -->
<script nonce="{{ nonce }}">
```

#### 🧪 Validação:
```bash
# Verificar que nonce está sendo gerado
curl -I http://localhost:5000 | grep -i "nonce"
```

**Tempo:** 30 minutos  
**Impacto:** 🔴 CRÍTICO → 🟢 RESOLVIDO

---

## 🟡 MÉDIA PRIORIDADE

### 2. Implementar Verificação CSRF Explícita

**Vulnerabilidade:** 10 rotas POST sem verificação CSRF explícita

#### 📍 Rotas Afetadas:
1. `meu_app/routes.py` - `/login`
2. `meu_app/pedidos/routes.py` - `/novo`
3. `meu_app/coletas/routes.py` - `/processar/<id>`
4. `meu_app/usuarios/routes.py` - `/`
5. `meu_app/financeiro/routes.py` - `/pagamento/<id>`
6. `meu_app/log_atividades/routes.py` - `/limpar`
7. `meu_app/estoques/routes.py` - `/novo`
8. `meu_app/clientes/routes.py` - `/novo`
9. `meu_app/produtos/routes.py` - `/novo`
10. `meu_app/apuracao/routes.py` - `/nova`

#### ✅ Solução Global (Recomendada):

**Opção 1: Configurar Flask-WTF (Já instalado)**

```python
# meu_app/__init__.py
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    
    # Habilitar CSRF globalmente
    csrf.init_app(app)
    
    # Configurar secret key (já deve ter)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Permitir CSRF em todas as rotas por padrão
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None  # Ou definir timeout
    
    return app
```

**Opção 2: Adicionar Verificação Manual**

Para cada rota POST, adicionar no início:

```python
from flask_wtf.csrf import validate_csrf
from werkzeug.exceptions import BadRequest

@app.route('/endpoint', methods=['POST'])
def endpoint():
    try:
        validate_csrf(request.form.get('csrf_token'))
    except BadRequest:
        abort(403, 'CSRF token inválido ou ausente')
    
    # Resto do código...
```

#### ✅ Solução Recomendada (Mais Simples):

**Verificar se já está protegido automaticamente:**

```python
# Criar script de teste: test_csrf_protection.py
from meu_app import create_app
import requests

app = create_app()

with app.test_client() as client:
    # Tentar POST sem CSRF
    response = client.post('/login', data={
        'usuario': 'teste',
        'senha': 'teste'
    })
    
    # Se retornar 400 ou 403, CSRF está ativo
    print(f"Status: {response.status_code}")
    if response.status_code in [400, 403]:
        print("✅ CSRF está ATIVO globalmente!")
    else:
        print("❌ CSRF precisa ser configurado")
```

#### 📝 Adicionar CSRF Token nos Templates:

Em todos os formulários HTML, adicionar:

```html
<form method="POST">
    {{ form.csrf_token }}  <!-- Se usando Flask-WTF Form -->
    <!-- OU -->
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    
    <!-- Resto do formulário -->
</form>
```

#### 🧪 Validação:
```bash
# Testar sem CSRF token (deve falhar)
curl -X POST http://localhost:5000/login \
  -d "usuario=admin&senha=123" \
  -v

# Deve retornar 400 ou 403
```

**Tempo:** 1-2 horas  
**Impacto:** 🟡 10 vulnerabilidades → 🟢 RESOLVIDO

---

## 🔵 BAIXA PRIORIDADE

### 3. Revisar Uso de `render_template_string`

**Vulnerabilidade:** XSS potencial em testes

#### 📍 Localização:
```python
# tests/security/test_csp.py:237
rendered = render_template_string(template)
```

#### ✅ Solução:

**Opção 1:** Adicionar validação no teste

```python
from markupsafe import escape

# ANTES
rendered = render_template_string(template)

# DEPOIS
rendered = render_template_string(template, 
    user_input=escape(user_input))
```

**Opção 2:** Usar template file em vez de string

```python
# Criar template file: tests/fixtures/test_template.html
# ANTES
template = "<html>{{ user_input }}</html>"
rendered = render_template_string(template)

# DEPOIS
rendered = render_template('test_template.html', user_input=user_input)
```

**Tempo:** 15 minutos  
**Impacto:** 🔵 BAIXO → 🟢 RESOLVIDO

---

## 📋 CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1: Correções Críticas (30 min)
- [ ] Implementar geração dinâmica de nonce
- [ ] Atualizar context processor
- [ ] Testar nonce em produção
- [ ] Commit: "fix(security): Remove hardcoded CSP nonce"

### Fase 2: CSRF Protection (1-2h)
- [ ] Verificar se Flask-WTF está instalado
- [ ] Configurar CSRFProtect globalmente
- [ ] Adicionar csrf_token em todos os formulários
- [ ] Testar cada rota POST
- [ ] Criar testes automatizados
- [ ] Commit: "feat(security): Enable explicit CSRF protection"

### Fase 3: Melhorias Adicionais (15 min)
- [ ] Revisar render_template_string em testes
- [ ] Adicionar escape onde necessário
- [ ] Commit: "fix(security): Escape user input in tests"

### Fase 4: Validação Final (30 min)
- [ ] Executar auditoria novamente
- [ ] Verificar relatório
- [ ] Confirmar 0 vulnerabilidades HIGH/MEDIUM
- [ ] Atualizar documentação

---

## 🛡️ MELHORIAS ADICIONAIS (Opcional)

### Security Headers

Adicionar headers de segurança:

```python
# meu_app/__init__.py

@app.after_request
def security_headers(response):
    """Adiciona headers de segurança"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
```

### Configurar Flask-Talisman

```bash
pip install flask-talisman
```

```python
from flask_talisman import Talisman

Talisman(app, 
    force_https=True,
    strict_transport_security=True,
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'nonce-{nonce}'"],
        'style-src': ["'self'", "'unsafe-inline'"],
    }
)
```

### Monitoramento Contínuo

```bash
# Instalar pip-audit
pip install pip-audit

# Executar periodicamente
pip-audit

# Adicionar ao CI/CD
# .github/workflows/security.yml
- name: Check for vulnerabilities
  run: pip-audit
```

---

## 📊 IMPACTO ESPERADO

### Antes (Atual):
```
🔴 CRITICAL: 2
🟠 HIGH: 3
🟡 MEDIUM: 11
🔵 LOW: 1
───────────────
Total: 17
Nível: 🟡 MÉDIO
```

### Depois (Meta):
```
🔴 CRITICAL: 0 (-2)
🟠 HIGH: 0 (-3)
🟡 MEDIUM: 0 (-11)
🔵 LOW: 0-1 (-1)
───────────────
Total: 0-1
Nível: 🟢 BAIXO
```

---

## 🚀 ORDEM DE EXECUÇÃO RECOMENDADA

### Dia 1 (2-3 horas)
```bash
# 1. Corrigir token hardcoded
# Editar meu_app/__init__.py (adicionar nonce dinâmico)

# 2. Configurar CSRF
# Verificar/configurar Flask-WTF

# 3. Atualizar templates
# Adicionar csrf_token em formulários

# 4. Testar
python -m pytest tests/security/

# 5. Executar nova auditoria
python auditoria/security_audit.py
```

### Validação Final
```bash
# Confirmar nível BAIXO
grep -A 5 "RESUMO EXECUTIVO" auditoria/pentest_zap_resumo.json
```

---

## 📚 RECURSOS E REFERÊNCIAS

- 📖 [Flask-WTF CSRF Protection](https://flask-wtf.readthedocs.io/en/stable/csrf.html)
- 🔒 [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- 🛡️ [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- 📊 [Security Headers](https://securityheaders.com/)

---

## ✅ CRITÉRIOS DE SUCESSO

Para atingir **RISCO BAIXO**, o sistema deve:

- ✅ **0** vulnerabilidades CRITICAL
- ✅ **0** vulnerabilidades HIGH
- ✅ **0-2** vulnerabilidades MEDIUM (aceitáveis se bem documentadas)
- ✅ **0-5** vulnerabilidades LOW (aceitáveis)
- ✅ Passar em 100% dos testes de segurança
- ✅ Headers de segurança configurados
- ✅ CSRF ativo em todas as rotas POST
- ✅ Sem secrets hardcoded

---

## 📞 SUPORTE

Dúvidas durante a implementação?
- 📖 Consultar: `auditoria/RESUMO_EXECUTIVO.md`
- 🔍 Re-executar: `python auditoria/security_audit.py`
- 📧 Contato: security@sistemasap.com

---

**Última Atualização:** 12/10/2025  
**Versão:** 1.0  
**Status:** 📋 Pendente de Implementação

