# 🔍 Guia de Observabilidade - Sistema SAP

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Logging Estruturado](#logging-estruturado)
- [Métricas Prometheus](#métricas-prometheus)
- [Request Tracking](#request-tracking)
- [Uso Prático](#uso-prático)
- [Monitoramento](#monitoramento)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

O sistema implementa **observabilidade completa** através de três pilares:

1. **📝 Logs Estruturados JSON** - Rastreabilidade e debugging
2. **📊 Métricas Prometheus** - Monitoramento e alertas
3. **🔗 Request Tracking** - Correlação de eventos

### Benefícios

✅ **Debugging Rápido**: Correlação de logs via request_id  
✅ **Monitoramento Proativo**: Métricas em tempo real  
✅ **Análise de Performance**: Histogramas de latência  
✅ **Alertas Inteligentes**: Detecção automática de problemas  
✅ **Compliance**: Auditoria completa de requisições

---

## 📝 Logging Estruturado

### Características

- **Formato JSON** para fácil parsing
- **Request ID** automático para correlação
- **Contexto rico**: user_id, IP, endpoint, método
- **Rotação automática** de arquivos
- **Multi-nível**: DEBUG, INFO, WARNING, ERROR

### Formato de Log

```json
{
  "timestamp": "2025-10-08T00:00:00",
  "level": "INFO",
  "logger": "meu_app.pedidos",
  "message": "Pedido criado com sucesso",
  "request_id": "abc-123-def-456",
  "user_id": 42,
  "ip_address": "127.0.0.1",
  "method": "POST",
  "url": "http://localhost:5004/api/pedidos",
  "endpoint": "pedidos.criar",
  "pedido_id": 123,
  "valor_total": 1500.00
}
```

### Uso no Código

```python
from meu_app.obs import get_logger

logger = get_logger(__name__)

# Log simples
logger.info("Operação concluída")

# Log com contexto extra
logger.info("Pedido criado", extra={
    "pedido_id": 123,
    "valor_total": 1500.00,
    "itens_count": 5
})

# Log de erro
logger.error("Falha ao processar pagamento", extra={
    "pagamento_id": 456,
    "erro": str(e)
}, exc_info=True)
```

### Localização dos Logs

- **Arquivo**: `instance/logs/app.log`
- **Rotação**: 10MB por arquivo, 5 backups
- **Console**: Desenvolvimento apenas (formato legível)

### Níveis de Log

| Nível | Uso | Exemplo |
|-------|-----|---------|
| **DEBUG** | Detalhes técnicos | Queries SQL, cache hits |
| **INFO** | Eventos normais | Request iniciado, operação concluída |
| **WARNING** | Situações inesperadas | Rate limit próximo, cache miss |
| **ERROR** | Erros recuperáveis | Validação falhou, timeout |
| **CRITICAL** | Falhas graves | Sistema indisponível, dados corrompidos |

---

## 📊 Métricas Prometheus

### Endpoint de Métricas

```
GET /metrics
```

Retorna métricas no formato Prometheus para scraping.

### Métricas Disponíveis

#### 1. **Métricas HTTP**

```python
# Total de requisições
http_requests_total{method="POST",endpoint="pedidos.criar",status="200"} 1523

# Duração das requisições (histograma)
http_request_duration_seconds_bucket{method="POST",endpoint="pedidos.criar",le="0.5"} 1200
http_request_duration_seconds_sum{method="POST",endpoint="pedidos.criar"} 312.5
http_request_duration_seconds_count{method="POST",endpoint="pedidos.criar"} 1523

# Requisições em andamento
http_requests_in_progress{method="GET",endpoint="dashboard"} 3
```

#### 2. **Métricas de Negócio**

```python
# Operações de negócio
business_operations_total{module="pedidos",operation="criacao",status="success"} 842
business_operations_total{module="pagamentos",operation="aprovacao",status="error"} 12

# Duração de operações
business_operation_duration_seconds_sum{module="pedidos",operation="criacao"} 421.3
```

#### 3. **Métricas de Banco de Dados**

```python
# Queries executadas
database_queries_total{operation="SELECT",table="pedidos"} 5234
database_queries_total{operation="INSERT",table="pagamentos"} 892

# Duração de queries
database_query_duration_seconds_sum{operation="SELECT"} 12.5
```

#### 4. **Métricas de Cache**

```python
# Operações de cache
cache_operations_total{operation="get",result="hit"} 8432
cache_operations_total{operation="get",result="miss"} 1234
cache_operations_total{operation="set",result="success"} 1234
```

### Uso no Código

#### Rastreamento Automático de HTTP

```python
from meu_app.obs.metrics import track_request

@app.route('/api/pedidos')
@track_request  # Métricas automáticas
def listar_pedidos():
    return jsonify(pedidos)
```

#### Rastreamento de Operações de Negócio

```python
from meu_app.obs.metrics import track_business_operation

@track_business_operation('pedidos', 'criacao')
def criar_pedido(dados):
    # Métricas automáticas de duração e status
    pedido = Pedido(**dados)
    db.session.add(pedido)
    db.session.commit()
    return True, "Pedido criado", pedido
```

#### Métricas Manuais

```python
from meu_app.obs.metrics import (
    business_operation,
    track_db_query,
    track_cache_operation
)

# Operação de negócio
business_operation('pagamentos', 'aprovacao', 'success')

# Query de banco
track_db_query('SELECT', 'clientes')

# Operação de cache
track_cache_operation('get', 'hit')
```

---

## 🔗 Request Tracking

### Request ID Automático

Cada requisição recebe um **UUID único** que:
- ✅ É adicionado automaticamente nos logs
- ✅ É retornado no header `X-Request-ID`
- ✅ Permite correlacionar todos os eventos de uma requisição

### Fluxo de Rastreamento

```
1. Cliente faz request → Gera UUID
2. Middleware adiciona request_id no contexto (g.request_id)
3. Todos os logs incluem request_id automaticamente
4. Resposta retorna X-Request-ID header
5. Cliente pode reenviar X-Request-ID para debugging
```

### Exemplo de Correlação

**Request**:
```http
POST /api/pedidos HTTP/1.1
Host: localhost:5004
Content-Type: application/json
```

**Logs Correlacionados**:
```json
{"timestamp": "...", "request_id": "abc-123", "message": "Request iniciado", ...}
{"timestamp": "...", "request_id": "abc-123", "message": "Validando dados", ...}
{"timestamp": "...", "request_id": "abc-123", "message": "Pedido criado", ...}
{"timestamp": "...", "request_id": "abc-123", "message": "Request concluído", ...}
```

**Response**:
```http
HTTP/1.1 200 OK
X-Request-ID: abc-123
Content-Type: application/json
```

### Buscar Logs por Request ID

```bash
# Buscar todos os logs de uma requisição específica
grep "abc-123" instance/logs/app.log | jq '.'

# Ou usando ferramenta de análise
cat instance/logs/app.log | jq 'select(.request_id == "abc-123")'
```

---

## 🚀 Uso Prático

### 1. Debugging de Produção

**Problema**: Erro intermitente em produção

```bash
# 1. Cliente reporta erro e fornece request_id
# 2. Buscar logs da requisição
grep "request_id-do-cliente" instance/logs/app.log | jq '.'

# 3. Ver toda a jornada da requisição
# 4. Identificar ponto de falha
```

### 2. Análise de Performance

**Problema**: Endpoint lento

```bash
# 1. Acessar métricas Prometheus
curl http://localhost:5004/metrics

# 2. Ver latência P95 do endpoint
http_request_duration_seconds{endpoint="pedidos.criar",quantile="0.95"}

# 3. Identificar operações lentas nos logs
cat instance/logs/app.log | jq 'select(.duration_ms > 1000)'
```

### 3. Monitoramento de SLA

**Objetivo**: Garantir 99% das requisições < 500ms

```promql
# Prometheus Query
histogram_quantile(
  0.99,
  rate(http_request_duration_seconds_bucket[5m])
) < 0.5
```

### 4. Alertas Proativos

**Cenários**:

```promql
# Taxa de erro > 5%
rate(http_requests_total{status=~"5.."}[5m]) 
/ 
rate(http_requests_total[5m]) 
> 0.05

# Latência P95 > 2s
histogram_quantile(
  0.95,
  rate(http_request_duration_seconds_bucket[5m])
) > 2.0

# Operações de negócio falhando
rate(business_operations_total{status="error"}[5m]) > 10
```

---

## 📈 Monitoramento

### Setup Prometheus

**1. Configurar Prometheus** (`prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'sap-sistema'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:5004']
    metrics_path: '/metrics'
```

**2. Iniciar Prometheus**:

```bash
prometheus --config.file=prometheus.yml
```

**3. Acessar**:
- Prometheus: http://localhost:9090
- Métricas da app: http://localhost:5004/metrics

### Setup Grafana

**1. Adicionar Data Source**:
- Type: Prometheus
- URL: http://localhost:9090

**2. Criar Dashboard** com painéis:

```
📊 HTTP Requests Rate (req/s)
📊 HTTP Latency P50/P95/P99
📊 Error Rate (%)
📊 Requests In Progress
📊 Business Operations Rate
📊 Database Query Latency
📊 Cache Hit Ratio
```

### Queries Úteis

```promql
# Taxa de requisições por endpoint
rate(http_requests_total[5m])

# Latência média por endpoint
rate(http_request_duration_seconds_sum[5m]) 
/ 
rate(http_request_duration_seconds_count[5m])

# Taxa de erro
rate(http_requests_total{status=~"5.."}[5m])

# Top 5 endpoints mais lentos
topk(5, 
  rate(http_request_duration_seconds_sum[5m]) 
  / 
  rate(http_request_duration_seconds_count[5m])
)

# Taxa de operações de negócio
rate(business_operations_total[5m])

# Hit rate do cache
rate(cache_operations_total{result="hit"}[5m])
/
rate(cache_operations_total{operation="get"}[5m])
```

---

## 🐛 Troubleshooting

### Problema: Logs não aparecem

**Solução**:
```python
# Verificar configuração
from meu_app.obs import get_logger
logger = get_logger(__name__)
logger.info("Teste de log")

# Verificar arquivo
cat instance/logs/app.log | tail -20
```

### Problema: Request ID não aparece nos logs

**Solução**:
```python
# Verificar que está em contexto de request
from flask import g
print(g.get('request_id', 'Não encontrado'))

# Verificar middleware
# setup_request_tracking deve estar sendo chamado
```

### Problema: Métricas não atualizam

**Solução**:
```bash
# 1. Verificar endpoint
curl http://localhost:5004/metrics

# 2. Verificar se decorators estão aplicados
# @track_request deve estar nas rotas

# 3. Verificar Prometheus scraping
# Ver logs do Prometheus
```

### Problema: Performance degradada

**Causas Comuns**:
- Logs em nível DEBUG em produção
- Muitas métricas com alta cardinalidade
- Arquivo de log muito grande sem rotação

**Soluções**:
```python
# 1. Ajustar nível de log
# config.py
LOG_LEVEL = 'INFO'  # Em produção

# 2. Limitar labels de métricas
# Evitar user_id, request_id como labels

# 3. Verificar rotação
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
```

---

## 📚 Referências

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Twelve-Factor App Logs](https://12factor.net/logs)
- [Logging Best Practices](https://www.dataset.com/blog/the-10-commandments-of-logging/)

---

## 🎯 Checklist de Produção

Antes de ir para produção, verifique:

- [ ] Logs configurados com nível INFO ou WARNING
- [ ] Rotação de logs ativada
- [ ] Prometheus configurado para scraping
- [ ] Grafana com dashboards básicos
- [ ] Alertas configurados (erro rate, latência)
- [ ] Retenção de logs definida (30 dias recomendado)
- [ ] Backup de logs configurado
- [ ] Documentação compartilhada com equipe

---

**Implementado por**: Sistema SAP - Fase 6  
**Data**: Outubro 2025  
**Versão**: 1.0

