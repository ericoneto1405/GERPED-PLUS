# 📡 Exemplos de Requisições API - Sistema SAP

## 📋 Índice

- [Healthchecks](#healthchecks)
- [Autenticação](#autenticação)
- [Clientes](#clientes)
- [Produtos](#produtos)
- [Pedidos](#pedidos)
- [Financeiro](#financeiro)
- [Métricas](#métricas)

---

## 🏥 Healthchecks

### Liveness Probe

```bash
# curl
curl http://localhost:5004/healthz

# httpie
http GET http://localhost:5004/healthz
```

**Resposta Esperada**:
```json
{
  "status": "healthy",
  "service": "sistema-sap",
  "timestamp": "2025-10-08T00:00:00.000000"
}
```

### Readiness Probe

```bash
# curl
curl http://localhost:5004/readiness

# httpie
http GET http://localhost:5004/readiness
```

**Resposta Esperada**:
```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "cache": true
  },
  "timestamp": "2025-10-08T00:00:00.000000"
}
```

---

## 🔐 Autenticação

### Login

```bash
# curl
curl -X POST http://localhost:5004/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "nome=admin&senha=admin123" \
  -c cookies.txt

# httpie
http --form POST http://localhost:5004/login \
  nome=admin \
  senha=admin123 \
  --session=./session.json
```

**Resposta**: Redirect 302 para dashboard

### Logout

```bash
# curl
curl -X GET http://localhost:5004/logout \
  -b cookies.txt

# httpie
http GET http://localhost:5004/logout \
  --session=./session.json
```

---

## 👥 Clientes

### Listar Clientes

```bash
# curl (com autenticação)
curl -X GET http://localhost:5004/clientes/ \
  -b cookies.txt

# httpie
http GET http://localhost:5004/clientes/ \
  --session=./session.json
```

### Criar Cliente

```bash
# curl
curl -X POST http://localhost:5004/clientes/criar \
  -b cookies.txt \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "nome=Cliente Novo" \
  -d "fantasia=Fantasia Ltda" \
  -d "cpf_cnpj=12345678901" \
  -d "endereco=Rua Exemplo, 123" \
  -d "cidade=São Paulo" \
  -d "telefone=11999999999"

# httpie
http --form POST http://localhost:5004/clientes/criar \
  --session=./session.json \
  nome="Cliente Novo" \
  fantasia="Fantasia Ltda" \
  cpf_cnpj="12345678901" \
  endereco="Rua Exemplo, 123" \
  cidade="São Paulo" \
  telefone="11999999999"
```

### Buscar Cliente (API JSON)

```bash
# curl
curl -X GET "http://localhost:5004/clientes/api/buscar?q=Cliente" \
  -b cookies.txt \
  -H "Accept: application/json"

# httpie
http GET "http://localhost:5004/clientes/api/buscar?q=Cliente" \
  --session=./session.json
```

**Resposta**:
```json
{
  "clientes": [
    {
      "id": 1,
      "nome": "Cliente Novo",
      "fantasia": "Fantasia Ltda",
      "cpf_cnpj": "12345678901"
    }
  ]
}
```

---

## 📦 Produtos

### Listar Produtos

```bash
# curl
curl -X GET http://localhost:5004/produtos/ \
  -b cookies.txt

# httpie
http GET http://localhost:5004/produtos/ \
  --session=./session.json
```

### Criar Produto

```bash
# curl
curl -X POST http://localhost:5004/produtos/criar \
  -b cookies.txt \
  -F "nome=Produto Novo" \
  -F "codigo_interno=PROD001" \
  -F "categoria=CERVEJA" \
  -F "preco_medio_compra=15.50" \
  -F "ean=7891234567890"

# httpie
http --form POST http://localhost:5004/produtos/criar \
  --session=./session.json \
  nome="Produto Novo" \
  codigo_interno="PROD001" \
  categoria="CERVEJA" \
  preco_medio_compra="15.50" \
  ean="7891234567890"
```

---

## 🛒 Pedidos

### Listar Pedidos

```bash
# curl
curl -X GET http://localhost:5004/pedidos/ \
  -b cookies.txt

# httpie
http GET http://localhost:5004/pedidos/ \
  --session=./session.json
```

### Criar Pedido

```bash
# curl
curl -X POST http://localhost:5004/pedidos/criar \
  -b cookies.txt \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "cliente_id=1" \
  -d "produto_1=1" \
  -d "quantidade_1=10" \
  -d "preco_venda_1=20.00"

# httpie
http --form POST http://localhost:5004/pedidos/criar \
  --session=./session.json \
  cliente_id=1 \
  produto_1=1 \
  quantidade_1=10 \
  preco_venda_1=20.00
```

---

## 💰 Financeiro

### Dashboard Financeiro

```bash
# curl
curl -X GET http://localhost:5004/financeiro/ \
  -b cookies.txt

# httpie
http GET http://localhost:5004/financeiro/ \
  --session=./session.json
```

### Aprovar Pagamento (API)

```bash
# curl
curl -X POST http://localhost:5004/financeiro/api/aprovar-pagamento \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"pagamento_id": 1, "senha_admin": "admin123"}'

# httpie
http POST http://localhost:5004/financeiro/api/aprovar-pagamento \
  --session=./session.json \
  pagamento_id:=1 \
  senha_admin="admin123"
```

**Resposta**:
```json
{
  "sucesso": true,
  "mensagem": "Pagamento aprovado com sucesso"
}
```

---

## 📊 Métricas

### Prometheus Metrics

```bash
# curl
curl http://localhost:5004/metrics

# httpie
http GET http://localhost:5004/metrics
```

**Resposta (Prometheus format)**:
```
# HELP http_requests_total Total de requisições HTTP
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="main.dashboard",status="200"} 1523

# HELP http_request_duration_seconds Duração das requisições HTTP
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="main.dashboard",le="0.5"} 1200
```

---

## 🧪 Smoke Tests

### Script de Smoke Test

```bash
#!/bin/bash
# smoke_test.sh - Testa endpoints críticos

BASE_URL="http://localhost:5004"

echo "🔍 Testando endpoints críticos..."

# 1. Healthcheck
echo -n "  healthz... "
curl -sf "$BASE_URL/healthz" > /dev/null && echo "✅" || echo "❌"

# 2. Readiness
echo -n "  readiness... "
curl -sf "$BASE_URL/readiness" > /dev/null && echo "✅" || echo "❌"

# 3. Metrics
echo -n "  metrics... "
curl -sf "$BASE_URL/metrics" > /dev/null && echo "✅" || echo "❌"

# 4. Docs
echo -n "  docs... "
curl -sf "$BASE_URL/docs" > /dev/null && echo "✅" || echo "❌"

# 5. Login page
echo -n "  login... "
curl -sf "$BASE_URL/login" > /dev/null && echo "✅" || echo "❌"

echo ""
echo "✅ Smoke tests concluídos!"
```

**Uso**:
```bash
chmod +x smoke_test.sh
./smoke_test.sh

# Ou via Make
make smoke
```

---

## 🎯 Coleção Postman/Insomnia

### Healthchecks Collection

```json
{
  "name": "Sistema SAP - Healthchecks",
  "requests": [
    {
      "name": "Healthz",
      "method": "GET",
      "url": "{{base_url}}/healthz"
    },
    {
      "name": "Readiness",
      "method": "GET",
      "url": "{{base_url}}/readiness"
    },
    {
      "name": "Metrics",
      "method": "GET",
      "url": "{{base_url}}/metrics"
    }
  ],
  "environments": {
    "dev": {
      "base_url": "http://localhost:5004"
    },
    "prod": {
      "base_url": "https://sap.exemplo.com"
    }
  }
}
```

---

## 📚 Mais Exemplos

Acesse a documentação interativa em:

**http://localhost:5004/docs**

Lá você encontrará:
- 📖 Todos os endpoints documentados
- 🧪 Interface "Try it out" para testar
- 📝 Schemas de request/response
- 🔧 Exemplos prontos para copiar

---

**Autor**: Sistema SAP - Fase 10  
**Data**: Outubro 2025

