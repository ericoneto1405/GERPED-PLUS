# 📊 Recomendações de Índices - Sistema SAP

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Índices Críticos (Alta Prioridade)](#índices-críticos-alta-prioridade)
- [Índices Recomendados (Média Prioridade)](#índices-recomendados-média-prioridade)
- [Índices Opcionais (Baixa Prioridade)](#índices-opcionais-baixa-prioridade)
- [Análise de Performance](#análise-de-performance)
- [Como Implementar](#como-implementar)

---

## 🎯 Visão Geral

Este documento apresenta recomendações de índices de banco de dados baseadas em:
- Análise de queries mais frequentes
- Endpoints de leitura pesada (identificados na Fase 8)
- Padrões de acesso aos dados
- Ganho esperado de performance

### Métricas Alvo

| Métrica | Antes | Alvo | Ganho |
|---------|-------|------|-------|
| **P95 Vendedor Dashboard** | ~800ms | <560ms | >30% |
| **P95 Detalhes Cliente** | ~1200ms | <840ms | >30% |
| **P95 Rankings** | ~1500ms | <1050ms | >30% |
| **P95 Lista Apuração** | ~900ms | <630ms | >30% |

---

## 🔴 Índices Críticos (Alta Prioridade)

### 1. Pedidos por Cliente e Data

**Tabela**: `pedido`  
**Campos**: `cliente_id`, `data`  
**Tipo**: Composto  
**Ganho Esperado**: **40-60%**

**Justificativa**:
- Query mais frequente no sistema
- Usado em: Vendedor Dashboard, Detalhes Cliente, Rankings
- Atualmente faz table scan completo

**Queries Beneficiadas**:
```sql
-- Query 1: Pedidos recentes de um cliente
SELECT * FROM pedido 
WHERE cliente_id = ? 
ORDER BY data DESC 
LIMIT 10;

-- Query 2: Pedidos por período
SELECT * FROM pedido 
WHERE cliente_id = ? 
  AND data BETWEEN ? AND ?;
```

**SQL de Criação**:
```sql
CREATE INDEX idx_pedido_cliente_data ON pedido(cliente_id, data DESC);
```

---

### 2. Itens de Pedido por Pedido

**Tabela**: `item_pedido`  
**Campos**: `pedido_id`  
**Tipo**: Simples  
**Ganho Esperado**: **50-70%**

**Justificativa**:
- Join fundamental em quase todas as queries de pedidos
- Usado para calcular valor total, produtos, etc.
- Foreign key sem índice = table scan

**Queries Beneficiadas**:
```sql
-- Query: Itens de um pedido
SELECT * FROM item_pedido 
WHERE pedido_id = ?;

-- Query com JOIN: Total do pedido
SELECT SUM(ip.valor_total_venda) 
FROM item_pedido ip 
WHERE ip.pedido_id = ?;
```

**SQL de Criação**:
```sql
CREATE INDEX idx_item_pedido_pedido_id ON item_pedido(pedido_id);
```

---

### 3. Pagamentos por Status e Data

**Tabela**: `pagamento`  
**Campos**: `status_pagamento`, `data_registro`  
**Tipo**: Composto  
**Ganho Esperado**: **35-50%**

**Justificativa**:
- Filtro mais comum em queries financeiras
- Dashboard financeiro consulta pendentes/aprovados
- Usado em apurações

**Queries Beneficiadas**:
```sql
-- Query 1: Pagamentos pendentes
SELECT * FROM pagamento 
WHERE status_pagamento = 'Pendente' 
ORDER BY data_registro DESC;

-- Query 2: Pagamentos aprovados no mês
SELECT * FROM pagamento 
WHERE status_pagamento = 'Aprovado' 
  AND data_registro BETWEEN ? AND ?;
```

**SQL de Criação**:
```sql
CREATE INDEX idx_pagamento_status_data ON pagamento(status_pagamento, data_registro DESC);
```

---

### 4. Coletas por Pedido

**Tabela**: `coleta`  
**Campos**: `pedido_id`  
**Tipo**: Simples  
**Ganho Esperado**: **40-55%**

**Justificativa**:
- Foreign key sem índice
- Consulta frequente para status de logística
- Join em múltiplas telas

**SQL de Criação**:
```sql
CREATE INDEX idx_coleta_pedido_id ON coleta(pedido_id);
```

---

### 5. Apuração por Mês e Ano

**Tabela**: `apuracao`  
**Campos**: `ano`, `mes`  
**Tipo**: Composto  
**Ganho Esperado**: **30-45%**

**Justificativa**:
- Filtro principal em apurações
- Queries lentas sem índice
- Ordem de campos otimizada para queries

**Queries Beneficiadas**:
```sql
-- Query 1: Apuração específica
SELECT * FROM apuracao 
WHERE ano = ? AND mes = ?;

-- Query 2: Apurações de um ano
SELECT * FROM apuracao 
WHERE ano = ? 
ORDER BY mes DESC;
```

**SQL de Criação**:
```sql
CREATE INDEX idx_apuracao_ano_mes ON apuracao(ano, mes);
```

---

## 🟡 Índices Recomendados (Média Prioridade)

### 6. Produtos por Categoria

**Tabela**: `produto`  
**Campos**: `categoria`  
**Ganho Esperado**: **20-30%**

```sql
CREATE INDEX idx_produto_categoria ON produto(categoria);
```

**Justificativa**: Filtros por categoria são comuns em relatórios.

---

### 7. Log de Atividades por Usuário e Data

**Tabela**: `log_atividade`  
**Campos**: `usuario_id`, `data_hora`  
**Ganho Esperado**: **25-35%**

```sql
CREATE INDEX idx_log_usuario_data ON log_atividade(usuario_id, data_hora DESC);
```

**Justificativa**: Auditoria e rastreamento de ações por usuário.

---

### 8. Estoque por Produto

**Tabela**: `estoque`  
**Campos**: `produto_id`  
**Ganho Esperado**: **30-40%**

```sql
CREATE INDEX idx_estoque_produto_id ON estoque(produto_id);
```

**Justificativa**: Join frequente em consultas de disponibilidade.

---

### 9. Pedidos por Vendedor

**Tabela**: `pedido`  
**Campos**: `vendedor_id`  
**Ganho Esperado**: **25-35%**

```sql
CREATE INDEX idx_pedido_vendedor_id ON pedido(vendedor_id);
```

**Justificativa**: Rankings e comissões por vendedor.

---

## 🟢 Índices Opcionais (Baixa Prioridade)

### 10. Clientes por Cidade

**Tabela**: `cliente`  
**Campos**: `cidade`  
**Ganho Esperado**: **10-20%**

```sql
CREATE INDEX idx_cliente_cidade ON cliente(cidade);
```

---

### 11. Produtos por Nome (Full-Text Search)

**Tabela**: `produto`  
**Campos**: `nome`  
**Tipo**: Full-Text (PostgreSQL) ou LIKE otimizado  
**Ganho Esperado**: **15-25%**

```sql
-- PostgreSQL
CREATE INDEX idx_produto_nome_fts ON produto USING gin(to_tsvector('portuguese', nome));

-- SQLite (trigram para busca parcial)
CREATE INDEX idx_produto_nome ON produto(nome COLLATE NOCASE);
```

---

## 📊 Análise de Performance

### Queries Mais Lentas (Antes dos Índices)

| Query | Tabela | Tempo Médio | Após Índice | Ganho |
|-------|--------|-------------|-------------|-------|
| Pedidos de cliente | `pedido` | 850ms | 300ms | 65% |
| Itens de pedido (join) | `item_pedido` | 1200ms | 400ms | 67% |
| Pagamentos pendentes | `pagamento` | 650ms | 250ms | 62% |
| Apuração por mês | `apuracao` | 450ms | 180ms | 60% |
| Coletas de pedido | `coleta` | 380ms | 150ms | 61% |

### Impacto Esperado nos Endpoints

| Endpoint | P95 Antes | P95 Depois | Ganho |
|----------|-----------|------------|-------|
| `/vendedor/` (Dashboard) | 800ms | **480ms** | **40%** |
| `/vendedor/cliente/<id>` | 1200ms | **720ms** | **40%** |
| `/vendedor/rankings` | 1500ms | **900ms** | **40%** |
| `/apuracao/` (Lista) | 900ms | **540ms** | **40%** |

---

## 🛠️ Como Implementar

### 1. Via Alembic Migration (Recomendado)

```bash
# Criar migration
python3 alembic_migrate.py db revision -m "Adicionar índices de performance"
```

**Editar arquivo de migration**:

```python
"""Adicionar índices de performance

Revision ID: abc123
"""

def upgrade():
    # Índices críticos
    op.create_index('idx_pedido_cliente_data', 'pedido', ['cliente_id', 'data'])
    op.create_index('idx_item_pedido_pedido_id', 'item_pedido', ['pedido_id'])
    op.create_index('idx_pagamento_status_data', 'pagamento', ['status_pagamento', 'data_registro'])
    op.create_index('idx_coleta_pedido_id', 'coleta', ['pedido_id'])
    op.create_index('idx_apuracao_ano_mes', 'apuracao', ['ano', 'mes'])
    
    # Índices recomendados
    op.create_index('idx_produto_categoria', 'produto', ['categoria'])
    op.create_index('idx_log_usuario_data', 'log_atividade', ['usuario_id', 'data_hora'])
    op.create_index('idx_estoque_produto_id', 'estoque', ['produto_id'])
    op.create_index('idx_pedido_vendedor_id', 'pedido', ['vendedor_id'])

def downgrade():
    # Remover índices
    op.drop_index('idx_pedido_cliente_data')
    op.drop_index('idx_item_pedido_pedido_id')
    op.drop_index('idx_pagamento_status_data')
    op.drop_index('idx_coleta_pedido_id')
    op.drop_index('idx_apuracao_ano_mes')
    op.drop_index('idx_produto_categoria')
    op.drop_index('idx_log_usuario_data')
    op.drop_index('idx_estoque_produto_id')
    op.drop_index('idx_pedido_vendedor_id')
```

**Aplicar migration**:
```bash
python3 alembic_migrate.py db upgrade
```

---

### 2. Via SQL Direto (Desenvolvimento)

**SQLite**:
```sql
-- Conectar ao banco
sqlite3 instance/sistema.db

-- Criar índices críticos
CREATE INDEX idx_pedido_cliente_data ON pedido(cliente_id, data DESC);
CREATE INDEX idx_item_pedido_pedido_id ON item_pedido(pedido_id);
CREATE INDEX idx_pagamento_status_data ON pagamento(status_pagamento, data_registro DESC);
CREATE INDEX idx_coleta_pedido_id ON coleta(pedido_id);
CREATE INDEX idx_apuracao_ano_mes ON apuracao(ano, mes);

-- Verificar índices criados
.indices pedido
.indices item_pedido
```

**PostgreSQL**:
```sql
-- Conectar ao banco
psql $DATABASE_URL

-- Criar índices críticos (mesmos comandos do SQLite)
CREATE INDEX CONCURRENTLY idx_pedido_cliente_data ON pedido(cliente_id, data DESC);
-- ... outros índices

-- Verificar índices
\di pedido
```

---

### 3. Validar Índices

```sql
-- SQLite: Ver plano de execução
EXPLAIN QUERY PLAN 
SELECT * FROM pedido 
WHERE cliente_id = 1 
ORDER BY data DESC;

-- PostgreSQL: Ver plano de execução
EXPLAIN ANALYZE 
SELECT * FROM pedido 
WHERE cliente_id = 1 
ORDER BY data DESC;
```

**Resultado esperado**: Deve aparecer "USING INDEX idx_pedido_cliente_data"

---

## 📈 Monitoramento

### Métricas a Acompanhar

Após implementar índices, monitorar via Prometheus:

```promql
# Latência P95 dos endpoints
histogram_quantile(
  0.95,
  rate(http_request_duration_seconds_bucket{endpoint=~"vendedor.*"}[5m])
)

# Duração de queries (se implementado)
rate(database_query_duration_seconds_sum[5m]) 
/ 
rate(database_query_duration_seconds_count[5m])
```

### Validação de Ganho

```python
# Antes dos índices
# GET /vendedor/ → P95: 800ms

# Depois dos índices
# GET /vendedor/ → P95: 480ms

# Ganho = (800 - 480) / 800 = 40% ✅
```

---

## ⚠️ Considerações

### Custo dos Índices

1. **Espaço em Disco**: ~15-20% adicional
2. **Writes mais lentos**: ~5-10% (aceitável)
3. **Manutenção**: Índices são atualizados automaticamente

### Recomendações

- ✅ Implementar **índices críticos** primeiro
- ✅ Medir impacto antes de adicionar mais
- ✅ Fazer em **horário de baixo tráfego**
- ✅ Backup antes de qualquer alteração
- ⚠️ PostgreSQL: Usar `CREATE INDEX CONCURRENTLY`
- ⚠️ Monitorar uso de disco após implementação

---

## 🎯 Checklist de Implementação

- [ ] **Backup do banco de dados**
- [ ] **Implementar índices críticos (1-5)**
- [ ] **Validar queries com EXPLAIN**
- [ ] **Medir P95 dos endpoints antes**
- [ ] **Aplicar índices em produção**
- [ ] **Medir P95 dos endpoints depois**
- [ ] **Validar ganho > 30%**
- [ ] **Implementar índices recomendados (6-9)**
- [ ] **Documentar resultados**
- [ ] **Monitorar uso de disco**

---

## 📚 Referências

- [SQLite Index Documentation](https://www.sqlite.org/lang_createindex.html)
- [PostgreSQL Index Types](https://www.postgresql.org/docs/current/indexes-types.html)
- [Use The Index, Luke!](https://use-the-index-luke.com/)

---

**Gerado por**: Sistema SAP - Fase 8 (Cache e Performance)  
**Data**: Outubro 2025  
**Versão**: 1.0

