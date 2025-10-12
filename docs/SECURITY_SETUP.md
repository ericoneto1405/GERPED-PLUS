# 🔒 GUIA DE CONFIGURAÇÃO DE SEGURANÇA

## 📋 Índice

1. [Gestão de Segredos](#gestão-de-segredos)
2. [Configuração de Ambiente](#configuração-de-ambiente)
3. [Dependências Seguras](#dependências-seguras)
4. [Pre-Commit Hooks](#pre-commit-hooks)
5. [Verificação de Segurança](#verificação-de-segurança)

---

## 🔐 Gestão de Segredos

### Desenvolvimento Local

1. **Copiar template de variáveis:**
   ```bash
   cp .env.example .env
   ```

2. **Gerar SECRET_KEY segura:**
   ```bash
   python -c 'import secrets; print(secrets.token_hex(32))'
   ```

3. **Editar `.env` com valores reais:**
   ```bash
   # NUNCA commite o arquivo .env!
   nano .env
   ```

### Produção (AWS Secrets Manager)

1. **Instalar AWS CLI:**
   ```bash
   pip install awscli boto3
   aws configure
   ```

2. **Criar segredo no AWS Secrets Manager:**
   ```bash
   aws secretsmanager create-secret \
       --name sap/production \
       --description "Credenciais do Sistema SAP" \
       --secret-string '{
         "SECRET_KEY": "your-secret-key-here",
         "DATABASE_URL": "postgresql://...",
         "REDIS_URL": "redis://...",
         "GOOGLE_CREDS_PATH": "/path/to/creds.json"
       }'
   ```

3. **Habilitar rotação automática:**
   ```bash
   aws secretsmanager rotate-secret \
       --secret-id sap/production \
       --rotation-lambda-arn arn:aws:lambda:...
   ```

4. **Configurar aplicação:**
   ```bash
   export USE_AWS_SECRETS=true
   export AWS_REGION=us-east-1
   ```

### Rotação de Segredos

Execute mensalmente:

```bash
python scripts/rotate_secrets.py
```

Ou configure cron:

```cron
0 0 1 * * /path/to/rotate_secrets.py
```

---

## ⚙️ Configuração de Ambiente

### Variáveis Obrigatórias

| Variável | Descrição | Desenvolvimento | Produção |
|----------|-----------|-----------------|----------|
| `SECRET_KEY` | Chave de criptografia | Min 32 chars | AWS Secrets Manager |
| `DATABASE_URL` | String de conexão DB | SQLite local | PostgreSQL |
| `REDIS_URL` | URL do Redis | Opcional | Obrigatório |

### Variáveis Opcionais

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `FORCE_HTTPS` | Forçar redirecionamento HTTPS | `false` |
| `HSTS_ENABLED` | Habilitar HSTS | `false` |
| `ENABLE_2FA` | Habilitar 2FA para admins | `false` |
| `LOG_LEVEL` | Nível de log | `INFO` |

---

## 📦 Dependências Seguras

### Instalação com Hashes

```bash
# Instalar com verificação de hashes SHA256
pip install --require-hashes -r requirements.txt
```

### Atualizar Dependências

```bash
# Compilar requirements.txt com hashes
./scripts/compile-requirements.sh

# Atualizar pacote específico
pip-compile --upgrade-package flask requirements.in

# Atualizar tudo
pip-compile --upgrade requirements.in
```

### Verificar Vulnerabilidades

```bash
# Safety - CVE check
safety check --json

# Bandit - SAST
bandit -r meu_app/ -c pyproject.toml
```

---

## 🪝 Pre-Commit Hooks

### Instalação

```bash
# Instalar pre-commit
pip install pre-commit

# Instalar hooks
pre-commit install
```

### Uso

```bash
# Executar em todos os arquivos
pre-commit run --all-files

# Executar hook específico
pre-commit run bandit

# Pular hooks (emergência)
git commit --no-verify
```

### Hooks Configurados

- ✅ **Bandit** - SAST para Python
- ✅ **Safety** - CVE check
- ✅ **detect-secrets** - Detecta credenciais
- ✅ **detect-private-key** - Detecta chaves privadas
- ✅ **Black** - Formatação
- ✅ **isort** - Ordenação de imports
- ✅ **Ruff** - Linting
- ✅ **MyPy** - Type checking

---

## 🔍 Verificação de Segurança

### Scan Completo

```bash
./scripts/security-check.sh
```

### Checklist Manual

- [ ] SECRET_KEY não é padrão
- [ ] .env não está no repositório
- [ ] requirements.txt tem hashes SHA256
- [ ] Todos os formulários têm CSRF token
- [ ] Nenhum arquivo sensível commitado
- [ ] .gitignore configurado corretamente
- [ ] Pre-commit hooks instalados
- [ ] Safety check passou
- [ ] Bandit não reportou issues críticas

---

## 🚨 Resposta a Incidentes

### Vazamento de Segredo

1. **Revogar imediatamente:**
   ```bash
   # Rotacionar SECRET_KEY
   python scripts/rotate_secrets.py
   
   # Revogar credenciais AWS
   aws iam delete-access-key --access-key-id AKIAXXXXXXX
   ```

2. **Invalidar sessões:**
   ```bash
   redis-cli FLUSHDB
   ```

3. **Atualizar aplicação:**
   ```bash
   git pull
   docker-compose restart
   ```

4. **Notificar time:**
   - Slack: #security-incidents
   - Email: security@example.com

### Vulnerabilidade Detectada

1. **Atualizar dependência:**
   ```bash
   pip-compile --upgrade-package pacote-vulneravel requirements.in
   pip install -r requirements.txt
   ```

2. **Testar:**
   ```bash
   pytest tests/
   ./scripts/security-check.sh
   ```

3. **Deployar:**
   ```bash
   git commit -m "security: fix CVE-XXXX-XXXX"
   git push
   ```

---

## 📚 Referências

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [pip-tools](https://github.com/jazzband/pip-tools)
- [pre-commit](https://pre-commit.com/)
- [Bandit](https://bandit.readthedocs.io/)
- [Safety](https://pyup.io/safety/)

---

**Última atualização:** Outubro 2025  
**Mantenedor:** Equipe SAP Security

