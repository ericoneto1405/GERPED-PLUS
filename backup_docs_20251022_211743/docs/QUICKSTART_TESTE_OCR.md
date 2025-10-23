# 🚀 QUICKSTART: Testar OCR no Financeiro

**5 minutos para verificar se tudo está funcionando**

---

## ✅ Pré-requisitos

- [x] Servidor rodando: `python run.py`
- [x] Navegador aberto
- [x] Comprovante PIX em mãos (JPG/PNG/PDF)

---

## 🧪 Teste 1: Diagnóstico Rápido (30 segundos)

```bash
python diagnostico_ocr_console.py
```

**Você deve ver**:
```
✅ Credenciais Google Vision: ENCONTRADO
✅ Quota OCR: 992/1000 disponíveis
✅ CSP Configuration: Nonce desabilitado
✅ Endpoint OCR: /financeiro/processar-recibo-ocr registrado
```

Se tudo ✅ → prossiga para Teste 2  
Se algo ❌ → consulte `FLUXO_FINANCEIRO_COLETA.md` seção Troubleshooting

---

## 🧪 Teste 2: OCR com Seu Comprovante (1 minuto)

```bash
python test_ocr_direto.py /caminho/seu_comprovante.jpg
```

**Resultado esperado**:
```
✅ SUCESSO: Valor R$ 150.50 extraído!
```

**Se falhar**:
- Verificar se arquivo existe
- Tentar com outro comprovante
- Ver quota OCR (deve ter disponível)

---

## 🧪 Teste 3: No Navegador (3 minutos)

### Passo 1: Abrir Financeiro

```
http://localhost:5004/financeiro
```

### Passo 2: Selecionar Pedido Pendente

Clique em "Lançar Pagamento" em qualquer pedido com saldo a pagar

### Passo 3: Abrir Console

Pressione **F12** → aba **Console**

### Passo 4: Upload do Comprovante

1. Clique em "Escolher arquivo"
2. Selecione seu comprovante PIX
3. **AGUARDE** 2-5 segundos

### Passo 5: Verificar Logs

**Você DEVE ver no console**:
```
🚀 Script financeiro_pagamento.js carregado
✅ Formulário encontrado
📁 Arquivo selecionado, iniciando upload OCR...
🌐 Enviando request para: /financeiro/processar-recibo-ocr
📥 Response status: 200
✅ OCR retorno completo: {valor_encontrado: 150.50, ...}
💰 Valor encontrado pelo OCR: 150.50
✅ Campo valor preenchido com: 150.50
```

### Passo 6: Verificar Campo

- Campo "Valor a Pagar" preencheu automaticamente? ✅
- Valor está correto? ✅

### Passo 7: Salvar

1. Revise o valor
2. Clique "Confirmar Pagamento"
3. Verifique mensagem de sucesso

---

## 🎯 Resultados Esperados

### ✅ Tudo Funcionando

- Console mostra logs detalhados
- Campo "Valor a Pagar" preenche sozinho
- Sem erros de CSP
- Pagamento salva com sucesso
- Status do pedido atualiza

### ⚠️ Se Campo Não Preenche

**Diagnóstico Rápido**:

1. **Console tem erros?**
   - CSP violation → Ver `config.py` linha 82-103
   - Fetch failed → Verificar endpoint com `diagnostico_ocr_console.py`
   - TypeError → Verificar tipo de `valor_encontrado`

2. **OCR retornou null?**
   ```
   ⚠️ OCR retornou: {valor_encontrado: null}
   ```
   - Normal! Google Vision não identificou valor
   - Digite manualmente
   - Tente com outro comprovante mais claro

3. **Sem logs no console?**
   - Script não carregou
   - Verificar CSP: `CSP_NONCE_SOURCES` deve estar vazio
   - Reiniciar servidor

---

## 🔧 Troubleshooting Rápido

### Erro: "Limite de OCR atingido"

```bash
python diagnostico_ocr_console.py | grep "Quota OCR"
```

Se mostrar 1000/1000 → Aguardar próximo mês ou aumentar limite

### Erro: "Credenciais não encontradas"

Verificar:
```bash
ls /Users/ericobrandao/keys/gvision-credentials.json
```

Se não existir → Configurar caminho em `meu_app/financeiro/config.py`

### Erro: CSP bloqueia script

Verificar `config.py`:
```python
# Deve estar assim:
CSP_NONCE_SOURCES = []  # Vazio!
```

Reiniciar servidor após mudança.

---

## 📞 Ajuda

### Documentação Completa

```bash
cat FLUXO_FINANCEIRO_COLETA.md
```

### Relatório de Diagnóstico

```bash
cat RELATORIO_DIAGNOSTICO_FINANCEIRO_OCR.md
```

### Teste End-to-End

```bash
python test_fluxo_financeiro_coleta.py
```

---

## ✅ Checklist Rápido

- [ ] Diagnóstico rodou sem erros
- [ ] OCR extraiu valor do seu comprovante
- [ ] Console mostra logs detalhados
- [ ] Campo preenche automaticamente
- [ ] Pagamento salva com sucesso
- [ ] Status do pedido atualiza

**Se todos ✅ → Sistema está 100% funcional!** 🎉

**Se algum ❌ → Consulte `FLUXO_FINANCEIRO_COLETA.md` para debug detalhado**

---

**Tempo Total**: 5 minutos  
**Dificuldade**: Fácil  
**Ajuda**: `FLUXO_FINANCEIRO_COLETA.md`
