# ⚠️ MIGRATIONS ANTIGAS - DEPRECATED

## ⚠️ AVISO IMPORTANTE

**Este diretório contém migrations manuais antigas que foram DESCONTINUADAS.**

A partir de Outubro/2025, o projeto utiliza **Alembic + Flask-Migrate** para gerenciamento
profissional de migrations com versionamento automático.

## 📂 Estrutura Nova

```
migrations/              ← Nova estrutura Alembic
├── versions/            ← Migrations versionadas
├── alembic.ini         ← Configuração
├── env.py              ← Ambiente Alembic
└── README              ← Documentação

migrations_old/          ← Este diretório (arquivado)
```

## 📋 Histórico de Migrations Manuais

### Migrações de Campos
- `migracao_add_campos_comprovante.py` - Adiciona campos extraídos do comprovante via OCR
- `migracao_add_conferente.py` - Adiciona campos do conferente
- `migracao_add_id_transacao.py` - Adiciona campo ID da transação
- `migracao_add_recibo_meta.py` - Adiciona metadados do recibo
- `migracao_add_recibo.py` - Adiciona campos básicos do recibo

### Migrações de Sistema
- `migracao_logistica.sql` - Script SQL para migração do módulo logística
- `migrar_logistica_para_coletas.py` - Script Python para migração completa

## ✅ Status

**Todas as migrações antigas foram aplicadas e arquivadas.**

## 🚀 Como Usar o Novo Sistema

Consulte a documentação principal em:
- `docs/GUIA_DESENVOLVEDOR.md`
- `migrations/README`

Comandos principais:
```bash
# Criar migração
python3 alembic_migrate.py db migrate -m "Descrição"

# Aplicar migrations
python3 alembic_migrate.py db upgrade

# Reverter última migration
python3 alembic_migrate.py db downgrade

# Ver status
python3 alembic_migrate.py db current
```
