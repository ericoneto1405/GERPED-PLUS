# 🔧 Como Instalar e Usar o OWASP ZAP para Pentest Dinâmico

## 📦 Instalação do OWASP ZAP

### macOS (Homebrew)
```bash
brew install --cask owasp-zap
```

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install zaproxy
```

### Windows
Baixe o instalador em: https://www.zaproxy.org/download/

---

## 🚀 Como Executar Pentest Dinâmico

### 1. Iniciar o Servidor Flask
```bash
cd /Users/ericobrandao/Projects/SAP
python run.py
```

### 2. Executar OWASP ZAP via GUI (Recomendado para primeiro uso)

```bash
# Abrir ZAP
open -a "OWASP ZAP"

# Ou no Linux
zaproxy

# Configurar:
1. Automated Scan
2. URL: http://localhost:5000
3. Use traditional spider
4. Attack Mode: Standard
5. Start Attack
```

### 3. Executar OWASP ZAP via CLI (Automatizado)

```bash
#!/bin/bash

# Configurações
TARGET="http://localhost:5000"
ZAP_PORT=8090
REPORT_DIR="/Users/ericobrandao/Projects/SAP/auditoria"

# Iniciar ZAP em modo daemon
zap.sh -daemon -port $ZAP_PORT -config api.disablekey=true &
ZAP_PID=$!

# Aguardar inicialização
echo "Aguardando ZAP inicializar..."
sleep 20

# Spider (rastreamento)
echo "Fase 1: Spider..."
curl "http://localhost:$ZAP_PORT/JSON/spider/action/scan/?url=$TARGET"
sleep 10

# Aguardar spider completar
while [ $(curl -s "http://localhost:$ZAP_PORT/JSON/spider/view/status/" | jq -r '.status') != "100" ]; do
    sleep 5
done

# Active Scan
echo "Fase 2: Active Scan..."
curl "http://localhost:$ZAP_PORT/JSON/ascan/action/scan/?url=$TARGET"

# Aguardar scan completar
while [ $(curl -s "http://localhost:$ZAP_PORT/JSON/ascan/view/status/" | jq -r '.status') != "100" ]; do
    sleep 10
done

# Gerar relatórios
echo "Gerando relatórios..."
curl "http://localhost:$ZAP_PORT/OTHER/core/other/htmlreport/" > "$REPORT_DIR/zap_dynamic_report.html"
curl "http://localhost:$ZAP_PORT/JSON/core/view/alerts/" > "$REPORT_DIR/zap_dynamic_alerts.json"

# Shutdown ZAP
curl "http://localhost:$ZAP_PORT/JSON/core/action/shutdown/"
kill $ZAP_PID

echo "✅ Pentest dinâmico concluído!"
echo "📄 Relatórios em: $REPORT_DIR"
```

---

## 🔐 Autenticação no ZAP

Para testar áreas autenticadas:

### Método 1: Session Management (GUI)

1. **Tools** → **Options** → **Authentication**
2. Configurar:
   - Form-based authentication
   - Login URL: `http://localhost:5000/login`
   - Username field: `usuario`
   - Password field: `senha`
3. **Add User** e inserir credenciais de teste

### Método 2: Script de Autenticação

```python
# authentication_script.py
def authenticate(helper, paramsValues, credentials):
    msg = helper.prepareMessage()
    msg.setRequestHeader("POST http://localhost:5000/login HTTP/1.1")
    msg.setRequestBody(f"usuario={credentials.getParam('usuario')}&senha={credentials.getParam('senha')}")
    helper.sendAndReceive(msg)
    return msg
```

---

## 📊 Comparação: Análise Estática vs Dinâmica

| Aspecto | Estática (Atual) | Dinâmica (ZAP) |
|---------|------------------|----------------|
| **Velocidade** | ⚡ Muito Rápido (segundos) | 🐢 Lento (minutos/horas) |
| **Cobertura** | 📚 Todo o código | 🌐 Apenas código executado |
| **Falsos Positivos** | 🟡 Médio | 🟢 Baixo |
| **Tipos de Vulnerabilidades** | Padrões de código | Comportamento real |
| **Setup** | ✅ Pronto | 🔧 Requer instalação |
| **Autenticação** | ❌ Não testa | ✅ Testa fluxos autenticados |

---

## 🎯 Recomendação

### Use Análise Estática (Atual) para:
- ✅ Auditorias rápidas
- ✅ CI/CD pipelines
- ✅ Desenvolvimento local
- ✅ Code reviews

### Use Análise Dinâmica (ZAP) para:
- ✅ Testes completos de segurança
- ✅ Validação de configuração
- ✅ Teste de fluxos autenticados
- ✅ Compliance e auditorias formais

---

## 🔄 Automatizar Ambos

```yaml
# .github/workflows/security.yml
name: Security Audit

on:
  push:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * 1'  # Segunda-feira às 2h

jobs:
  static-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Static Security Audit
        run: python auditoria/security_audit.py
      
      - name: Upload Reports
        uses: actions/upload-artifact@v2
        with:
          name: security-reports
          path: auditoria/*.html
  
  dynamic-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start Application
        run: |
          python run.py &
          sleep 10
      
      - name: ZAP Scan
        uses: zaproxy/action-full-scan@v0.4.0
        with:
          target: 'http://localhost:5000'
```

---

## 📚 Recursos Adicionais

- 📖 [OWASP ZAP Documentation](https://www.zaproxy.org/docs/)
- 🎓 [ZAP Getting Started Guide](https://www.zaproxy.org/getting-started/)
- 🎥 [Video Tutorials](https://www.zaproxy.org/videos/)
- 💬 [ZAP User Group](https://groups.google.com/g/zaproxy-users)

---

## 🆘 Troubleshooting

### ZAP não inicia
```bash
# Verificar porta em uso
lsof -i :8090

# Matar processo
kill $(lsof -t -i:8090)
```

### Scan muito lento
```bash
# Reduzir threads
zap.sh -daemon -config scanner.threadPerHost=1

# Desabilitar scanners pesados
# Via GUI: Tools → Options → Active Scan → Policy
```

### Memória insuficiente
```bash
# Aumentar heap
zap.sh -daemon -Xmx4g  # 4GB de RAM
```

---

**Dúvidas?** Consulte a documentação oficial ou abra uma issue no projeto.

