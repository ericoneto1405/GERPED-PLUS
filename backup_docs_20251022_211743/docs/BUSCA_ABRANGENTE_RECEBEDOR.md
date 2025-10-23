# 🔍 Busca Abrangente de Dados do Recebedor

## 🎯 Como Funciona Agora

### Busca Inteligente (3 Etapas)

#### 1. Encontrar TODOS os dados no texto
- Busca **todos** os CNPJs (não importa onde estão)
- Busca **todos** os emails/PIX (não importa onde estão)
- Busca **todos** os nomes após palavras-chave

#### 2. Filtrar pelos dados da empresa
- CNPJ da empresa: `30080209000416`
- PIX da empresa: `pix@gruposertao.com`

#### 3. Validar se encontrou
- ✅ Se encontrou PIX da empresa → CORRETO
- ✅ Se encontrou CNPJ da empresa → CORRETO
- ⚠️ Se encontrou outros → INCORRETO

---

## 📋 Formatos de CNPJ Suportados

### Todos reconhecidos e normalizados:

| Formato no Comprovante | CNPJ Limpo | Status |
|------------------------|------------|--------|
| `30080209000416` | 30080209000416 | ✅ |
| `30.080.209/0004-16` | 30080209000416 | ✅ |
| `30.080.209/004-16` | 30080209000416 | ✅ |
| `300802090004-16` | 30080209000416 | ✅ |
| `30-080-209-0004-16` | 30080209000416 | ✅ |

**Regex**: Remove **TODOS** caracteres não-numéricos e compara!

---

## 📧 Formatos de PIX Suportados

| Tipo | Exemplo | Status |
|------|---------|--------|
| Email | pix@gruposertao.com | ✅ |
| Email (case insensitive) | PIX@GRUPOSERTAO.COM | ✅ |
| Telefone | +55 11 98765-4321 | ✅ |
| Chave aleatória | abc-123-def-456-ghi | ✅ |

---

## 🧪 Exemplo de Texto Real

### Texto do Comprovante:
```
Mercado Pago
Comprovante de Pagamento

De: Erico Neto
Email: ericoneto@hotmail.com

Para: Mariana Esporte
Email: lima.juliano@uol.com.br
CNPJ: 30.080.209/0004-16

Valor: R$ 1.100,00
```

### O Sistema Encontra:

1. **Emails**: 
   - ericoneto@hotmail.com (pagador)
   - lima.juliano@uol.com.br (outro)
   - **Nenhum é pix@gruposertao.com** ⚠️

2. **CNPJs**:
   - 30.080.209/0004-16 → 30080209000416
   - **É o CNPJ da empresa!** ✅

### Resultado da Validação:

```
Check 1: PIX → ⚠️ Diferente (0 pontos)
Check 2: CNPJ → ✅ Correto (40 pontos)

Confiança: 50%
Status: ⚠️ PARCIALMENTE VÁLIDO
```

---

## 🔧 Vantagens da Busca Abrangente

### ✅ Funciona Independente do Layout

**Comprovante Tipo 1** (Banco tradicional):
```
FAVORECIDO:
Nome: GRUPO SERTÃO
CNPJ: 30.080.209/0004-16
```

**Comprovante Tipo 2** (PIX):
```
Recebedor: pix@gruposertao.com
30080209000416
```

**Comprovante Tipo 3** (Mercado Pago):
```
Para
Grupo Sertão LTDA
Email: pix@gruposertao.com
```

**Todos funcionam!** ✅

---

### ✅ Normalização Automática

O sistema **remove automaticamente**:
- Pontos (.)
- Traços (-)
- Barras (/)
- Espaços

**Compara apenas números!**

```python
"30.080.209/0004-16" → "30080209000416"
"30.080.209/004-16"  → "30080209000416"  # Sem zero
"300802090004-16"    → "30080209000416"
```

---

## 📊 Fluxo de Validação

```
┌─────────────────────────────────────┐
│ 1. OCR extrai texto do comprovante  │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│ 2. Busca TODOS emails no texto      │
│    Encontrou: 3 emails               │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│ 3. Verifica se algum é da empresa   │
│    pix@gruposertao.com? SIM ✅       │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│ 4. Busca TODOS CNPJs no texto       │
│    Encontrou: 2 CNPJs                │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│ 5. Normaliza e compara               │
│    30.080.209/0004-16 → 30080209000416 │
│    É igual ao da empresa? SIM ✅     │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│ 6. Calcula confiança                 │
│    PIX: 40 pts + CNPJ: 40 pts = 80   │
│    Confiança: 100% ✅                 │
└──────────────┬──────────────────────┘
               │
               ↓
┌─────────────────────────────────────┐
│ 7. Mostra box VERDE no frontend      │
│    "✅ Pagamento para conta CORRETA" │
└─────────────────────────────────────┘
```

---

## 🎯 Configuração Simples

```python
# meu_app/financeiro/config.py

# Dados para buscar no comprovante:
RECEBEDOR_PIX = 'pix@gruposertao.com'
RECEBEDOR_CNPJ = '30080209000416'  # Apenas números!
```

**O sistema busca por esses valores em QUALQUER formato no texto!**

---

## ✅ Resumo

- ✅ Busca PIX em **qualquer lugar** do texto
- ✅ Busca CNPJ em **qualquer lugar** do texto  
- ✅ Remove **automaticamente** pontos/traços/barras
- ✅ Compara **apenas números**
- ✅ Funciona com **qualquer layout** de comprovante
- ✅ Validação visual **grande e visível**

---

**Teste agora com seus comprovantes reais!** 🚀
