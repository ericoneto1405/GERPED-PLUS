# 🔍 DEBUG - Problema de Upload OCR no Financeiro

## 📊 Problema Reportado

**Sintoma**: Campo "Valor a Pagar" não preenche automaticamente após upload de recibo  
**Módulo**: Financeiro - Lançar Pagamento  
**Funcionalidade**: OCR automático de recibos

---

## ✅ Verificações Já Realizadas

1. ✅ Endpoint `/financeiro/processar-recibo-ocr` **registrado**
2. ✅ Google Vision credentials **encontradas**
3. ✅ JavaScript `financeiro_pagamento.js` **existe**
4. ✅ Logs de debug **adicionados**

---

## 🧪 PASSO A PASSO PARA TESTAR

### 1. Reiniciar Servidor

```bash
# Parar servidor atual (Ctrl+C)

# Limpar cache
rm -rf meu_app/__pycache__
rm -rf meu_app/financeiro/__pycache__

# Reiniciar
python run.py
```

---

### 2. Acessar Página de Pagamento

1. Abra: http://localhost:5004/financeiro
2. Clique em "Lançar Pagamento" em qualquer pedido pendente
3. Abra o **Console do Browser** (F12 → Console)

---

### 3. Verificar Console - Carregamento Inicial

**Você DEVE ver**:
```
🚀 Script financeiro_pagamento.js carregado
✅ Formulário encontrado
📍 OCR URL: /financeiro/processar-recibo-ocr
📍 Elementos: {reciboInput: true, valorInput: true, idTransacaoInput: true, ocrStatus: true}
✅ Listener de upload registrado no campo recibo
```

**Se NÃO aparecer**:
- ❌ CSP está bloqueando o script
- ❌ Script não está carregando
- **Solução**: Reportar logs de erro do console

---

### 4. Fazer Upload de Arquivo

1. Clique em "Escolher arquivo" no campo **Recibo de Pagamento**
2. Selecione **qualquer imagem** (JPG, PNG) ou PDF
3. Aguarde 2-5 segundos

---

### 5. Verificar Console - Durante Upload

**Você DEVE ver**:
```
📁 Arquivo selecionado, iniciando upload OCR...
📁 Arquivo: recibo.jpg - Tamanho: 123456 bytes
🌐 Enviando request para: /financeiro/processar-recibo-ocr
📥 Response status: 200
✅ OCR retorno completo: {valor_encontrado: 150.50, ...}
💰 Valor encontrado pelo OCR: 150.50
💰 Valor parseado: 150.5
✅ Campo valor preenchido com: 150.50
```

---

### 6. Cenários Possíveis

#### ✅ Cenário 1: Tudo OK (Campo preenche)
```
✅ OCR retorno completo: {valor_encontrado: 150.50, ocr_status: 'success'}
✅ Campo valor preenchido com: 150.50
```
**Ação**: Nenhuma, está funcionando!

---

#### ⚠️ Cenário 2: Script não carrega
**Console mostra**:
```
Refused to load script 'financeiro_pagamento.js' because it violates CSP
```

**Solução**:
```python
# config.py - adicionar em DevelopmentConfig
"script-src": [
    "'self'",
    "'unsafe-inline'",
    "https://cdn.jsdelivr.net",
    ...
]
```

---

#### ⚠️ Cenário 3: Fetch bloqueado por CSP
**Console mostra**:
```
🌐 Enviando request para: /financeiro/processar-recibo-ocr
❌ ERRO no fetch do OCR: TypeError: Failed to fetch
```

**Causa**: CSP bloqueando `connect-src`

**Solução**:
```python
# config.py - já aplicado
"connect-src": ["'self'", "https://cdn.jsdelivr.net"],
```

---

#### ⚠️ Cenário 4: OCR retorna erro
**Console mostra**:
```
✅ OCR retorno completo: {valor_encontrado: null, ocr_status: 'failed', ocr_error: '...'}
```

**Causas possíveis**:
1. Limite de quota OCR atingido
2. Google Vision falhou
3. Arquivo não é recibo válido

**Solução**:
- Verificar logs do servidor
- Verificar quota OCR em `meu_app.models.OcrQuota`

---

#### ⚠️ Cenário 5: OCR OK mas valor null
**Console mostra**:
```
✅ OCR retorno completo: {valor_encontrado: null, ocr_status: 'success'}
⚠️ Nenhum dado encontrado no recibo
```

**Causa**: OCR não encontrou padrão de valor no recibo

**Solução**: Digite o valor manualmente (comportamento esperado)

---

#### ⚠️ Cenário 6: HTTP 400/500
**Console mostra**:
```
📥 Response status: 400
❌ ERRO no fetch do OCR: Error: HTTP 400: Bad Request
```

**Solução**: Verificar logs do servidor para ver erro específico

---

## 🔧 AÇÕES CORRETIVAS APLICADAS

### 1. Logs de Debug Adicionados
**Arquivo**: `meu_app/static/js/financeiro_pagamento.js`

- ✅ Log de carregamento do script
- ✅ Log de elementos encontrados
- ✅ Log de arquivo selecionado
- ✅ Log de request/response
- ✅ Log de parsing de valor
- ✅ Log de preenchimento de campo

---

### 2. CSP Configurado para Desenvolvimento
**Arquivo**: `config.py`

```python
class DevelopmentConfig:
    CSP_DIRECTIVES = {
        "script-src": ["'self'", "'unsafe-inline'", ...],
        "connect-src": ["'self'", "https://cdn.jsdelivr.net"],
    }
    CSP_NONCE_SOURCES = []  # Desabilitar nonce em dev
```

---

## 📝 REPORTAR RESULTADO

**Copie e envie**:
1. ✅ ou ❌ Script carregou?
2. ✅ ou ❌ Upload disparou?
3. ✅ ou ❌ Request foi enviado?
4. ✅ ou ❌ Response recebida?
5. ✅ ou ❌ Campo preencheu?
6. **Screenshot do console completo**

---

## 🎯 TESTE RÁPIDO ALTERNATIVO

Se quiser testar apenas o backend:

```bash
cd /Users/ericobrandao/Projects/SAP

# Criar arquivo de teste
echo "RECIBO PIX R$ 150,50" > /tmp/test_recibo.txt

# Testar OCR diretamente
python3 << 'EOF'
from meu_app import create_app
from meu_app.financeiro.ocr_service import OcrService
from config import DevelopmentConfig

app = create_app(DevelopmentConfig)

with app.app_context():
    # Simular processamento
    result = OcrService.process_receipt('/tmp/test_recibo.txt')
    print("Resultado OCR:", result)
EOF
```

---

## ✅ PRÓXIMOS PASSOS

Após o teste, com base nos logs do console:

1. **Se script não carrega** → Ajustar CSP
2. **Se OCR falha** → Verificar credenciais/quota
3. **Se valor é null** → Melhorar regex de extração
4. **Se tudo OK** → Problema resolvido! 🎉

---

**Debug adicionado por**: Cursor AI  
**Data**: 08/10/2025  
**Status**: Aguardando teste do usuário
