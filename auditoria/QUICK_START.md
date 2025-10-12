# ⚡ QUICK START: Reduzir Risco para BAIXO

**Tempo Total: 2-3 horas** | **Dificuldade: ⭐⭐⭐ Média**

---

## 🚀 Início Rápido (Copy & Paste)

### AÇÃO 1: Nonce Dinâmico (30 min)

```bash
# 1. Abrir arquivo
code meu_app/__init__.py

# 2. Adicionar ANTES de "return app" no final do create_app():
```

```python
    # Gerar nonce para CSP
    import secrets
    from flask import g
    
    @app.before_request
    def generate_nonce():
        """Gera nonce único para cada request"""
        g.nonce = secrets.token_urlsafe(16)
    
    @app.context_processor
    def inject_nonce():
        """Injeta nonce em todos os templates"""
        return dict(nonce=getattr(g, 'nonce', ''))
    
    return app
```

**✅ Testar:**
```bash
python run.py
# Acessar http://localhost:5000 e verificar source HTML
# Deve ter: nonce="[valor aleatório]"
```

---

### AÇÃO 2: CSRF Protection (1-2h)

#### Parte A: Configurar CSRF (15 min)

```bash
# 1. Abrir arquivo
code meu_app/__init__.py

# 2. Adicionar no TOPO do arquivo (após imports):
```

```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
```

```python
# 3. Adicionar DENTRO de create_app(), ANTES dos blueprints:

    # Configurar CSRF Protection
    csrf.init_app(app)
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None
```

**✅ Testar:**
```bash
python run.py
# Tentar fazer POST sem CSRF (deve falhar 400/403)
curl -X POST http://localhost:5000/login -d "usuario=teste&senha=teste"
```

#### Parte B: Atualizar Templates (45 min)

**6 arquivos para atualizar:**

1️⃣ **painel.html**
```html
<!-- Encontrar: <form method="GET" -->
<!-- Adicionar após <form>: -->
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

2️⃣ **comprovantes_pagamento.html**
```html
<!-- Procurar forms com method="post" ou method="get" -->
<!-- Adicionar csrf_token se houver POST -->
```

3️⃣ **relatorio_coletas.html**
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

4️⃣ **financeiro.html**
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

5️⃣ **vendedor/rankings.html**
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

6️⃣ **vendedor/dashboard.html**
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

**Comando rápido para encontrar forms:**
```bash
grep -r "method=" meu_app/templates/*.html | grep -i "post"
```

---

### AÇÃO 3: XSS em Testes (15 min)

```bash
# 1. Abrir arquivo
code tests/security/test_csp.py

# 2. Encontrar linha 237 e mudar:
```

```python
# ANTES:
rendered = render_template_string(template)

# DEPOIS:
from markupsafe import escape
rendered = render_template_string(template, 
    user_input=escape(request.args.get('input', '')))
```

---

## ✅ VALIDAÇÃO FINAL

```bash
# 1. Executar nova auditoria
cd /Users/ericobrandao/Projects/SAP
python auditoria/security_audit.py

# 2. Verificar resultado (deve mostrar):
# 🟢 BAIXO - 0-5 vulnerabilidades
# 🔴 CRITICAL: 0
# 🟠 HIGH: 0
# 🟡 MEDIUM: 0-2

# 3. Ver relatório
open auditoria/pentest_zap_relatorio.html

# 4. Commit
git add .
git commit -m "fix(security): Reduce risk level to LOW - implement nonce, CSRF, and XSS fixes"
```

---

## 🆘 TROUBLESHOOTING

### Problema 1: CSRF está bloqueando tudo
```python
# Adicionar exempt para APIs (se necessário)
from flask_wtf.csrf import csrf

@app.route('/api/endpoint')
@csrf.exempt
def api_endpoint():
    pass
```

### Problema 2: Nonce não aparece
```python
# Verificar se before_request está ANTES de return app
# Testar manualmente:
with app.app_context():
    with app.test_request_context():
        generate_nonce()
        print(g.nonce)  # Deve imprimir algo
```

### Problema 3: Template não renderiza csrf_token
```html
<!-- Verificar se form está dentro de {% block content %}{% endblock %} -->
<!-- Testar: -->
{{ csrf_token() }}
<!-- Se não funcionar, usar: -->
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

---

## 📋 CHECKLIST

Antes de começar:
- [ ] Fazer backup: `git commit -am "checkpoint before security fixes"`
- [ ] Ler plano completo: `cat auditoria/PLANO_ACAO_RISCO_BAIXO.md`

AÇÃO 1 - Nonce:
- [ ] Adicionar generate_nonce()
- [ ] Adicionar inject_nonce()
- [ ] Testar em localhost
- [ ] Verificar source HTML

AÇÃO 2 - CSRF:
- [ ] Importar CSRFProtect
- [ ] Inicializar csrf
- [ ] Testar POST sem token (deve falhar)
- [ ] Atualizar 6 templates
- [ ] Testar cada formulário

AÇÃO 3 - XSS:
- [ ] Adicionar escape em testes
- [ ] Rodar pytest
- [ ] Verificar testes passam

Validação:
- [ ] Nova auditoria
- [ ] Nível = BAIXO
- [ ] 0 HIGH/CRITICAL
- [ ] Commit final

---

## ⏱️ TIMELINE SUGERIDA

**09:00 - 09:30** ☕ Ler documentação + setup
**09:30 - 10:00** 🔴 AÇÃO 1: Nonce
**10:00 - 10:15** ☕ Break + testes
**10:15 - 11:15** 🟡 AÇÃO 2: CSRF (Parte A + B)
**11:15 - 11:30** 🔵 AÇÃO 3: XSS
**11:30 - 12:00** ✅ Validação + commit

**Total: 3 horas** ✨

---

## 📚 LINKS ÚTEIS

- Plano detalhado: `cat auditoria/PLANO_ACAO_RISCO_BAIXO.md`
- Análise: `python auditoria/aplicar_correcoes.py`
- Nova auditoria: `python auditoria/security_audit.py`

---

**Boa sorte! 🚀 Você consegue!**

