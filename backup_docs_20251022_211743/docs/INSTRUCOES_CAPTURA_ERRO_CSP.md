# 🔍 INSTRUÇÕES: Capturar Erros CSP no Console

## 📋 O Que Fazer Agora

### 1. Reiniciar Servidor (IMPORTANTE!)

```bash
# Parar servidor atual (Ctrl+C)

# Reiniciar com configurações atualizadas
cd /Users/ericobrandao/Projects/SAP
python run.py
```

**Por quê?** As correções CSP só funcionam após reiniciar.

---

### 2. Acessar Página de Pagamento

1. Abra: **http://localhost:5004/financeiro**
2. Clique em **"Lançar Pagamento"** em qualquer pedido pendente
   - Exemplo: Pedido #3 (falta R$ 400,00)

---

### 3. Abrir Console do Navegador

**Pressione**: `F12` (Chrome/Edge/Firefox)

**OU**

**Clique com direito** → **Inspecionar** → Aba **Console**

---

### 4. Fazer Upload do Comprovante

1. Na página de pagamento, localize o campo **"📄 Recibo de Pagamento"**
2. Clique em **"Escolher arquivo"**
3. Selecione seu comprovante PIX (JPG, PNG ou PDF)
4. **AGUARDE** 2-5 segundos

---

### 5. Capturar TODOS os Logs do Console

**Copie e cole TUDO que aparecer no console**, incluindo:

#### ✅ Logs Esperados (BOM):
```
🚀 Script financeiro_pagamento.js carregado
✅ Formulário encontrado
📍 OCR URL: /financeiro/processar-recibo-ocr
📁 Arquivo selecionado, iniciando upload OCR...
🌐 Enviando request para: /financeiro/processar-recibo-ocr
📥 Response status: 200
✅ OCR retorno completo: {...}
```

#### ❌ Erros CSP (RUIM):
```
Refused to execute inline script because it violates CSP...
Refused to load script from 'https://...'
Refused to connect to 'https://...'
```

#### ❌ Erros de Fetch (RUIM):
```
Failed to fetch
TypeError: NetworkError
CORS error
```

---

### 6. Verificar Campo "Valor a Pagar"

**Pergunta**: O campo preencheu automaticamente?

- ✅ **SIM** - Ótimo! OCR está funcionando
- ❌ **NÃO** - Precisamos ver por quê (logs do console dirão)

---

### 7. Verificar Logs do Servidor

**No terminal onde o servidor está rodando**, procure por:

```
[2025-10-08 ...] INFO Processando OCR...
[2025-10-08 ...] INFO Pagamento registrado...
```

OU

```
[2025-10-08 ...] ERROR Erro no OCR: ...
[2025-10-08 ...] WARNING OCR falhou: ...
```

---

## 📝 Me Envie

**Copie e cole aqui**:

1. ✅ ou ❌ **Servidor foi reiniciado?**
2. ✅ ou ❌ **Console mostra logs do script carregado?**
3. ✅ ou ❌ **Upload disparou (viu "Arquivo selecionado")?**
4. ✅ ou ❌ **Request foi enviado (viu "Enviando request")?**
5. ✅ ou ❌ **Response recebida (viu "Response status: 200")?**
6. ✅ ou ❌ **Campo "Valor a Pagar" preencheu?**
7. **TODOS os logs do console** (copie e cole tudo)
8. **Erros do servidor** (se houver)

---

## 🎯 Com Essas Informações

Vou poder identificar **exatamente**:

- Se CSP está bloqueando algo
- Se endpoint OCR está acessível
- Se Google Vision está funcionando
- Se JavaScript está processando corretamente
- Qual o erro específico que está acontecendo

---

**Aguardo seus logs para continuar o diagnóstico!** 🔍
