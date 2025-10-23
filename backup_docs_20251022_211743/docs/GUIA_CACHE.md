# 💾 Guia Prático de Cache - Sistema SAP

## 🎯 Visão Geral

Guia prático para usar o sistema de cache inteligente com invalidação por evento implementado na Fase 8.

---

## 🚀 Início Rápido

### 1. Aplicar Cache em um Endpoint

```python
from meu_app.cache import cached_with_invalidation

@app.route('/minha-rota')
@cached_with_invalidation(
    timeout=600,  # 10 minutos
    key_prefix='minha_rota',
    invalidate_on=['evento.criado']
)
def minha_rota():
    # Query pesada aqui
    dados = calcular_dados_pesados()
    return render_template('template.html', dados=dados)
```

### 2. Invalidar Cache ao Criar/Atualizar

```python
from meu_app.cache import invalidate_cache

def criar_pedido(dados):
    pedido = Pedido(**dados)
    db.session.add(pedido)
    db.session.commit()
    
    # Invalidar todos os caches relacionados
    invalidate_cache(['pedido.criado'])
    
    return pedido
```

---

## 📚 Decorators Disponíveis

### `@cached()`

Cache simples com TTL.

**Parâmetros**:
- `timeout`: Segundos até expirar (default: 300)
- `key_prefix`: Prefixo da chave
- `unless`: Função que retorna True para pular cache
- `make_cache_key_fn`: Função custom para gerar chave

**Exemplo**:
```python
@cached(timeout=1800, key_prefix='relatorio_mensal')
def relatorio_mensal(mes, ano):
    return calcular_relatorio(mes, ano)
```

### `@cached_with_invalidation()`

Cache com invalidação automática por eventos.

**Parâmetros**:
- `timeout`: Segundos até expirar
- `key_prefix`: Prefixo da chave
- `invalidate_on`: Lista de eventos que invalidam

**Exemplo**:
```python
@cached_with_invalidation(
    timeout=600,
    key_prefix='dashboard_vendedor',
    invalidate_on=['pedido.criado', 'pedido.atualizado']
)
def dashboard_vendedor(vendedor_id):
    return calcular_dashboard(vendedor_id)
```

---

## 🔔 Eventos Disponíveis

### Pedidos
- `pedido.criado`
- `pedido.atualizado`
- `pedido.cancelado`

### Pagamentos
- `pagamento.aprovado`
- `pagamento.rejeitado`

### Coletas
- `coleta.concluida`

### Apuração
- `apuracao.criada`
- `apuracao.atualizada`

### Produtos/Clientes
- `produto.atualizado`
- `cliente.atualizado`

---

## 🎨 Padrões de Uso

### Padrão 1: Listagem com Filtros

```python
@cached_with_invalidation(
    timeout=300,
    key_prefix='lista_clientes',
    invalidate_on=['cliente.atualizado']
)
def listar_clientes():
    # Query params são incluídos automaticamente na chave
    filtro = request.args.get('filtro')
    clientes = Cliente.query.filter_by(filtro).all()
    return render_template('clientes.html', clientes=clientes)
```

### Padrão 2: Detalhes de Entidade

```python
@cached_with_invalidation(
    timeout=600,
    key_prefix='cliente_detalhes',
    invalidate_on=['cliente.atualizado', 'pedido.criado']
)
def detalhes_cliente(cliente_id):
    # cliente_id é incluído automaticamente na chave
    cliente = Cliente.query.get(cliente_id)
    pedidos = Pedido.query.filter_by(cliente_id=cliente_id).all()
    return render_template('detalhes.html', cliente=cliente, pedidos=pedidos)
```

### Padrão 3: Dashboard com Cálculos

```python
@cached_with_invalidation(
    timeout=900,  # 15 minutos para dashboards
    key_prefix='dashboard_financeiro',
    invalidate_on=['pagamento.aprovado', 'pedido.criado']
)
def dashboard_financeiro():
    # Cálculos pesados
    receita = calcular_receita_total()
    pendente = calcular_pendente()
    return render_template('dashboard.html', receita=receita, pendente=pendente)
```

### Padrão 4: Pular Cache para Usuários Autenticados

```python
from meu_app.cache import cached, unless_authenticated

@cached(
    timeout=600,
    key_prefix='home',
    unless=unless_authenticated  # Não cachear se logado
)
def home():
    return render_template('home.html')
```

---

## 🔧 Funções de Controle

### Invalidar Cache Manualmente

```python
from meu_app.cache import invalidate_cache

# Invalidar por evento
count = invalidate_cache('pedido.criado')
print(f"{count} chaves invalidadas")

# Invalidar múltiplos eventos
invalidate_cache(['pedido.criado', 'pagamento.aprovado'])

# Invalidar chaves específicas
invalidate_cache('pedido.atualizado', specific_keys=['pedido_detalhe_123'])
```

### Limpar Todo o Cache

```python
from meu_app.cache import clear_all_cache

# ⚠️ Use com cuidado!
if clear_all_cache():
    print("Cache limpo com sucesso")
```

### Estatísticas do Cache

```python
from meu_app.cache import get_cache_stats

stats = get_cache_stats()
print(f"Eventos mapeados: {stats['events_count']}")
print(f"Chaves no cache: {stats['keys_count']}")
print(f"Padrões de invalidação: {stats['invalidation_patterns']}")
```

---

## ⚡ Escolhendo o TTL Correto

| Tipo de Dados | TTL Recomendado | Razão |
|---------------|-----------------|-------|
| **Dashboards** | 10-15min | Atualização frequente mas não crítica |
| **Listagens** | 5-10min | Equilíbrio entre freshness e performance |
| **Detalhes** | 5min | Dados podem mudar frequentemente |
| **Relatórios** | 30-60min | Cálculos pesados, dados históricos |
| **Configurações** | 1-2h | Mudanças raras |
| **APIs públicas** | 1-5min | Freshness importante |

---

## 📊 Monitoramento de Cache

### Via Métricas Prometheus

```promql
# Hit rate do cache
rate(cache_operations_total{result="hit"}[5m])
/
rate(cache_operations_total{operation="get"}[5m])

# Total de operações de cache
rate(cache_operations_total[5m])

# Cache misses
rate(cache_operations_total{result="miss"}[5m])
```

### Via Logs

```bash
# Ver cache hits/misses
cat instance/logs/app.log | jq 'select(.message | contains("Cache"))'

# Contar hits
cat instance/logs/app.log | jq 'select(.message == "Cache HIT")' | wc -l
```

---

## 🐛 Troubleshooting

### Cache Não Está Funcionando

**Checklist**:
1. Decorator `@cached_with_invalidation` está aplicado?
2. Redis está rodando? (produção)
3. `CACHE_TYPE` está configurado corretamente?
4. Endpoint retorna dados serializáveis?

**Debug**:
```python
# Verificar configuração
from meu_app import cache as cache_instance
print(cache_instance.config)

# Testar manualmente
cache_instance.set('test', 'valor', timeout=60)
print(cache_instance.get('test'))  # Deve retornar 'valor'
```

### Cache Nunca Invalida

**Causas**:
1. Evento não está sendo disparado
2. Nome do evento diferente do mapeado
3. Redis pattern matching não funciona

**Solução**:
```python
# Invalidar manualmente
from meu_app.cache import invalidate_cache
invalidate_cache(['pedido.criado'])

# Ver chaves no cache
from meu_app.cache import get_cache_stats
print(get_cache_stats())
```

### Cache Hit Rate Baixo

**Causas**:
- TTL muito baixo
- Queries com muitos parâmetros únicos
- Invalidação muito frequente

**Soluções**:
- Aumentar TTL se possível
- Revisar lógica de invalidação
- Analisar métricas Prometheus

---

## 🎯 Boas Práticas

### ✅ DOs

- **Use invalidação por evento** (não TTL curto)
- **Escolha TTL baseado em criticidade** dos dados
- **Monitore hit rate** via Prometheus
- **Documente eventos** customizados
- **Teste invalidação** após implementar

### ❌ DON'Ts

- ❌ Cachear dados de usuário sensíveis sem segregação
- ❌ TTL > 1h para dados transacionais
- ❌ Invalidar "tudo" para qualquer evento
- ❌ Cachear responses com user_id no key (alta cardinalidade)
- ❌ Esquecer de invalidar cache ao atualizar dados

---

## 🚀 Próximos Passos

1. **Implementar índices críticos** (RECOMENDACOES_INDICES.md)
2. **Medir P95 antes** dos índices
3. **Aplicar índices em produção**
4. **Medir P95 depois** e validar >30%
5. **Configurar Redis** em produção
6. **Monitorar cache hit rate** via Grafana
7. **Ajustar TTLs** baseado em uso real

---

**Autor**: Sistema SAP  
**Fase**: 8 - Cache e Performance  
**Data**: Outubro 2025

