# 🗃️ Guia de Migrations com Alembic

## 📋 Índice

- [Introdução](#introdução)
- [Configuração](#configuração)
- [Comandos Básicos](#comandos-básicos)
- [Workflow de Desenvolvimento](#workflow-de-desenvolvimento)
- [Boas Práticas](#boas-práticas)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Introdução

O projeto utiliza **Alembic** via **Flask-Migrate** para gerenciamento profissional de migrations de banco de dados.

### Benefícios

✅ **Versionamento automático** - Rastreia mudanças no schema  
✅ **Upgrade/Downgrade** - Migra para frente e para trás  
✅ **Autogenerate** - Detecta alterações nos models automaticamente  
✅ **Multi-ambiente** - SQLite (dev) e PostgreSQL (prod)  
✅ **Histórico completo** - Auditoria de todas as mudanças

---

## ⚙️ Configuração

### Estrutura de Diretórios

```
migrations/
├── versions/               # Migrations versionadas
│   └── XXXXX_descricao.py # Arquivo de migration
├── alembic.ini            # Configuração do Alembic
├── env.py                 # Ambiente e contexto
├── script.py.mako         # Template para novas migrations
└── README                 # Documentação básica
```

### Dependências

```txt
Flask-Migrate==4.0.7
alembic==1.13.1
```

### Integração no App

```python
# meu_app/__init__.py
from flask_migrate import Migrate

migrate = Migrate()

def initialize_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)  # ← Alembic integrado
```

---

## 🚀 Comandos Básicos

### Script Wrapper

⚠️ **IMPORTANTE**: Use sempre o script `alembic_migrate.py` em vez de `flask db` diretamente.

```bash
# Este script força o uso do SQLite correto, ignorando DATABASE_URL do sistema
python3 alembic_migrate.py db <comando>
```

### Criar Nova Migration

```bash
# Autogenerate (recomendado)
python3 alembic_migrate.py db migrate -m "Adicionar campo email em Usuario"

# Manual (vazio)
python3 alembic_migrate.py db revision -m "Descrição personalizada"
```

### Aplicar Migrations

```bash
# Aplicar todas as pendentes
python3 alembic_migrate.py db upgrade

# Aplicar até uma versão específica
python3 alembic_migrate.py db upgrade abc123

# Aplicar apenas a próxima
python3 alembic_migrate.py db upgrade +1
```

### Reverter Migrations

```bash
# Reverter última migration
python3 alembic_migrate.py db downgrade -1

# Reverter até uma versão
python3 alembic_migrate.py db downgrade abc123

# Reverter tudo
python3 alembic_migrate.py db downgrade base
```

### Informações

```bash
# Ver versão atual
python3 alembic_migrate.py db current

# Ver histórico
python3 alembic_migrate.py db history

# Ver próximas migrations
python3 alembic_migrate.py db heads
```

---

## 🔄 Workflow de Desenvolvimento

### 1. Modificar Models

```python
# meu_app/models.py
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)  # ← NOVO CAMPO
```

### 2. Gerar Migration

```bash
python3 alembic_migrate.py db migrate -m "Adicionar email em Usuario"
```

**Output esperado:**
```
INFO  [alembic.autogenerate.compare] Detected added column 'usuario.email'
Generating migrations/versions/abc123_adicionar_email_em_usuario.py ... done
```

### 3. Revisar Migration Gerada

```python
# migrations/versions/abc123_adicionar_email_em_usuario.py
def upgrade():
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(120), nullable=True))
        batch_op.create_unique_constraint('uq_usuario_email', ['email'])
```

⚠️ **SEMPRE revise**:
- Nullable correto
- Default values
- Unique constraints nomeados
- Índices necessários

### 4. Aplicar Migration

```bash
python3 alembic_migrate.py db upgrade
```

### 5. Testar

```bash
# Testar downgrade
python3 alembic_migrate.py db downgrade -1

# Testar upgrade novamente
python3 alembic_migrate.py db upgrade
```

---

## 📖 Boas Práticas

### ✅ DOs

- **Sempre revisar** migrations autogeneradas
- **Testar upgrade E downgrade** antes de commitar
- **Nomear constraints** explicitamente
- **Commits atômicos**: 1 migration por commit
- **Mensagens descritivas**: "Adicionar campo X" > "Update"
- **Backup antes** de migrations em produção

### ❌ DON'Ts

- ❌ Editar migrations já aplicadas
- ❌ Deletar migrations do histórico
- ❌ Pular migrations (sempre sequencial)
- ❌ Migrations sem downgrade
- ❌ Migrations que perdem dados sem aviso

### 🔧 Migrations Seguras

```python
def upgrade():
    # ✅ BOM: Adicionar coluna nullable
    op.add_column('usuario', sa.Column('email', sa.String(120), nullable=True))
    
    # ✅ BOM: Adicionar com default
    op.add_column('pedido', sa.Column('status', sa.String(50), 
                                      server_default='Pendente'))
    
    # ⚠️  CUIDADO: NOT NULL sem default (falha se há dados)
    # op.add_column('usuario', sa.Column('email', sa.String(120), nullable=False))
    
    # ✅ MELHOR: Adicionar em 2 etapas
    # Migration 1: Adicionar nullable
    # Migration 2: Popular dados + tornar NOT NULL
```

---

## 🐛 Troubleshooting

### Erro: "No changes in schema detected"

**Causa**: Models não foram alterados ou não estão sendo importados.

**Solução**:
```python
# Verifique que models estão importados em meu_app/__init__.py
from .models import Usuario, Produto, Pedido  # etc
```

### Erro: "Constraint must have a name"

**Causa**: Alembic gerou constraint sem nome (bug conhecido no SQLite).

**Solução**: Edite a migration manualmente:
```python
# ❌ ANTES
batch_op.create_unique_constraint(None, ['email'])

# ✅ DEPOIS
batch_op.create_unique_constraint('uq_usuario_email', ['email'])
```

### Erro: "Can't locate revision identified by 'abc123'"

**Causa**: Migration foi deletada ou corrompida.

**Solução**: Recriar histórico:
```bash
# Verificar estado atual do banco
python3 alembic_migrate.py db current

# Se vazio, marcar manualmente
python3 alembic_migrate.py db stamp head
```

### Banco Dessincronizado

**Situação**: Banco tem tabelas mas Alembic não sabe disso.

**Solução**:
```bash
# 1. Backup do banco
cp instance/sistema.db instance/sistema.db.backup

# 2. Marcar como sincronizado (se schema está correto)
python3 alembic_migrate.py db stamp head

# 3. Ou recriar do zero
rm instance/sistema.db
python3 init_db.py
python3 alembic_migrate.py db stamp head
```

---

## 🚢 Deploy em Produção

### Checklist Pré-Deploy

- [ ] Backup do banco de produção
- [ ] Testar migrations em ambiente staging
- [ ] Revisar todos os downgrades
- [ ] Verificar impacto em queries existentes
- [ ] Planejar rollback se necessário

### Comandos de Deploy

```bash
# 1. Backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Aplicar migrations
python3 alembic_migrate.py db upgrade

# 3. Verificar
python3 alembic_migrate.py db current

# 4. Rollback (se necessário)
python3 alembic_migrate.py db downgrade -1
```

---

## 📚 Recursos Adicionais

- [Documentação Alembic](https://alembic.sqlalchemy.org/)
- [Flask-Migrate Docs](https://flask-migrate.readthedocs.io/)
- [SQLAlchemy Migrations](https://docs.sqlalchemy.org/en/20/core/metadata.html)

---

## 🆘 Suporte

**Problemas com migrations?**

1. Consulte este guia
2. Verifique `migrations_old/README.md` (histórico)
3. Contate o time de desenvolvimento

---

**Última atualização**: Outubro 2025  
**Versão**: 1.0  
**Projeto**: Sistema SAP

