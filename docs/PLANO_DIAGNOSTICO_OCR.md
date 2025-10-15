# 🔍 Plano de Diagnóstico - Problemas com OCR e PyTorch

**Data:** 15/10/2025  
**Problemas Reportados:**
1. OCR não está funcionando em várias tentativas
2. Leitura está errada quando funciona
3. Dúvidas sobre PyTorch estar treinado 100%
4. Dúvidas se PyTorch está sendo usado
5. Comprovantes podem estar sendo salvos nos clientes errados

---

## 🚨 Problemas Críticos Identificados

### 1. **CRÍTICO** - Modelo PyTorch com Overfitting Severo

**Arquivo:** `models/pytorch_validator/training_report.json`

**Métricas de Treinamento:**
```json
{
  "train_acc": [0.24, 0.94, 1.0, 1.0, 1.0],     // 100% no treino ✅
  "val_acc": [0.6, 0.4, 0.4, 0.4, 0.4],         // 40% na validação ❌
  "val_loss": [1.06, 1.15, 1.28, 1.43, 1.58]   // Perda aumentando ❌
}
```

**Análise:**
- ✅ Treino perfeito (100% acurácia)
- ❌ Validação péssima (40% acurácia)
- ❌ **OVERFITTING CLÁSSICO**: Modelo memorizou dados de treino mas não generaliza

**Consequência:**
- Modelo classifica incorretamente novos comprovantes
- Confiança pode ser enganosa
- Validações são não confiáveis

**Diagnóstico:** ⚠️ **MODELO NÃO ESTÁ TREINADO ADEQUADAMENTE**

### 2. **CRÍTICO** - Dataset Muito Pequeno

**training_report.json:**
```json
{
  "label_distribution": {
    "invalido": 12 documentos,
    "valido": 9 documentos,
    "suspeito": 1 documento
  }
}
```

**Total:** Apenas **22 documentos** no dataset!

**Problemas:**
- Dataset minúsculo para ML
- Distribuição desbalanceada (1 suspeito vs 12 inválidos)
- Impossível generalizar com tão poucos exemplos

**Recomendação Mínima:**
- Válidos: 100+ exemplos
- Inválidos: 100+ exemplos
- Suspeitos: 50+ exemplos

### 3. **ALTO** - Credenciais Google Vision Não Verificadas

**Arquivo:** `config.py` (Linha 30-32)

```python
GOOGLE_VISION_CREDENTIALS_PATH = os.getenv(
    'GOOGLE_APPLICATION_CREDENTIALS',
    '/Users/ericobrandao/keys/gvision-credentials.json'  # ← Path absoluto
)
```

**Problemas Potenciais:**
1. ❓ Arquivo existe neste caminho?
2. ❓ Credenciais são válidas?
3. ❓ API está habilitada no projeto Google Cloud?
4. ❓ Conta tem créditos disponíveis?
5. ❓ Variável de ambiente está setada?

### 4. **MÉDIO** - Quota OCR Pode Estar Esgotada

**Arquivo:** `config.py` (Linhas 25-26)

```python
OCR_ENFORCE_LIMIT = True
OCR_MONTHLY_LIMIT = 1000
```

**Verificação necessária:**
- Quantas OCRs foram usadas este mês?
- Quota foi atingida?
- Se sim, sistema bloqueia totalmente o OCR

### 5. **BAIXO** - Comprovantes Salvos com Pedido (Não Cliente)

**Análise da Estrutura:**

```python
# models.py
class Pagamento(db.Model):
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'))
    # ❌ NÃO TEM: cliente_id
```

**Como funciona:**
```
Comprovante → Pagamento → Pedido → Cliente
```

**Conclusão:**
- ✅ Comprovantes ESTÃO associados ao cliente correto
- ✅ Via relacionamento: Pagamento.pedido.cliente
- ✅ Design correto (um pedido = um cliente)

---

## 📋 Plano de Diagnóstico Completo

### Fase 1: Diagnóstico de Configuração

#### Checkpoint 1.1: Verificar Google Vision Credentials
```bash
# Verificar se arquivo existe
ls -la /Users/ericobrandao/keys/gvision-credentials.json

# Verificar variável de ambiente
echo $GOOGLE_APPLICATION_CREDENTIALS

# Verificar conteúdo (sem expor chaves)
cat /Users/ericobrandao/keys/gvision-credentials.json | jq '.project_id'
```

#### Checkpoint 1.2: Testar Conectividade Google Vision
```python
# Script de teste
from google.cloud import vision
client = vision.ImageAnnotatorClient()
# Se não der erro, credenciais OK
```

#### Checkpoint 1.3: Verificar Quota OCR
```sql
SELECT ano, mes, contador 
FROM ocr_quota 
WHERE ano = 2025 AND mes = 10
ORDER BY mes DESC;
```

**Verificar:**
- Se contador >= 1000 → Quota esgotada!

#### Checkpoint 1.4: Verificar PyTorch Instalado
```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
```

### Fase 2: Diagnóstico do Modelo PyTorch

#### Checkpoint 2.1: Verificar Arquivos do Modelo
```bash
ls -la models/pytorch_validator/
# Deve ter:
# - payment_validator.pt ✅ (modelo)
# - vocab.json ✅ (vocabulário)
# - labels.json ✅ (classes)
# - training_report.json ✅ (métricas)
```

#### Checkpoint 2.2: Analisar Métricas do Modelo
```python
# Ler training_report.json
{
  "val_acc": 0.4,  # ❌ 40% é PÉSSIMO!
  "train_acc": 1.0  # ✅ 100% indica overfitting
}
```

**Diagnóstico:**
- ⚠️ Modelo memorizou dados de treino
- ⚠️ Não consegue classificar novos documentos
- ⚠️ Precisa re-treinar com mais dados

#### Checkpoint 2.3: Testar Modelo Manualmente
```python
from meu_app.financeiro.pytorch_validator import PaymentValidatorService

texto_teste = "Comprovante de PIX no valor de R$ 150,00"
resultado = PaymentValidatorService.evaluate_text(texto_teste)

print(f"Label: {resultado['label']}")
print(f"Confidence: {resultado['confidence']}")
print(f"Scores: {resultado['scores']}")
```

**Verificar:**
- Se retorna erro → Modelo não carrega
- Se label aleatório → Modelo não funciona
- Se confidence baixa → Modelo inseguro

### Fase 3: Diagnóstico do OCR

#### Checkpoint 3.1: Testar OCR com Arquivo Real
```python
# Script de teste direto
from meu_app.financeiro.ocr_service import OcrService

resultado = OcrService.process_receipt('path/to/comprovante.pdf')

print(f"Texto extraído: {resultado.get('raw_text')}")
print(f"Valor: {resultado.get('amount')}")
print(f"ID Transação: {resultado.get('transaction_id')}")
print(f"Backend: {resultado.get('backend')}")
print(f"Fallback: {resultado.get('fallback_used')}")
print(f"Erro: {resultado.get('error')}")
```

#### Checkpoint 3.2: Verificar Logs de Erro
```bash
# Verificar logs recentes
tail -100 instance/logs/app.log | grep -i "ocr\|vision\|pytorch"
```

**Procurar por:**
- Erros de autenticação Google
- Timeout de API
- Quota excedida
- Falhas de extração

#### Checkpoint 3.3: Testar Fallback Local
```python
# Forçar uso de OCR local
export FINANCEIRO_OCR_LOCAL_ONLY=true

# Testar novamente
# Verificar se funciona com Tesseract
```

### Fase 4: Verificar Associação Cliente-Comprovante

#### Checkpoint 4.1: Query de Verificação
```sql
SELECT 
    pag.id AS pagamento_id,
    pag.valor,
    pag.caminho_recibo,
    ped.id AS pedido_id,
    cli.id AS cliente_id,
    cli.nome AS cliente_nome
FROM pagamento pag
JOIN pedido ped ON pag.pedido_id = ped.id
JOIN cliente cli ON ped.cliente_id = cli.id
ORDER BY pag.data_pagamento DESC
LIMIT 10;
```

**Verificar:**
- Cada pagamento tem pedido correto?
- Cada pedido tem cliente correto?
- Relacionamentos estão íntegros?

#### Checkpoint 4.2: Testar Recuperação de Comprovante
```python
# Ver se consegue acessar comprovante do cliente certo
from meu_app.models import Pagamento

pag = Pagamento.query.get(1)
print(f"Pagamento: {pag.id}")
print(f"Pedido: {pag.pedido.id}")
print(f"Cliente: {pag.pedido.cliente.nome}")
print(f"Recibo: {pag.caminho_recibo}")
```

---

## 🔧 Plano de Correções

### Correção 1: Re-treinar Modelo PyTorch (URGENTE)

**Problema:** Modelo atual tem 40% acurácia (inútil)

**Solução:**
1. Coletar mais dados (mínimo 100 por classe)
2. Balancear dataset
3. Aumentar regularização (dropout, weight decay)
4. Reduzir epochs para evitar overfitting
5. Re-treinar modelo

**Script:** `scripts/train_pytorch_validator.py`

**Comando:**
```bash
python scripts/train_pytorch_validator.py \
  --data data/comprovantes_dataset.jsonl \
  --epochs 10 \
  --dropout 0.5 \
  --early-stopping 3
```

### Correção 2: Verificar e Configurar Google Vision

**Passos:**
1. Verificar se credenciais existem
2. Testar conexão com API
3. Verificar quota/billing
4. Configurar variável de ambiente corretamente

**Teste:**
```bash
# Setar variável
export GOOGLE_APPLICATION_CREDENTIALS="/Users/ericobrandao/keys/gvision-credentials.json"

# Testar
python -c "from google.cloud import vision; client = vision.ImageAnnotatorClient(); print('OK')"
```

### Correção 3: Melhorar Extração de Dados OCR

**Problema:** Padrões regex podem estar muito restritivos ou incorretos

**Solução:**
1. Analisar comprovantes reais
2. Ajustar padrões regex
3. Adicionar mais variações
4. Testar com documentos diversos

**Arquivo:** `ocr_service.py`

### Correção 4: Adicionar Logs Detalhados

**Para debug, adicionar logs:**
```python
# No processo de OCR
logger.info(f"Iniciando OCR para arquivo: {file_path}")
logger.info(f"Backend usado: {backend}")
logger.info(f"Texto extraído (primeiros 200 chars): {text[:200]}")
logger.info(f"Dados extraídos: valor={amount}, id={transaction_id}")

# No PyTorch
logger.info(f"PyTorch ativo: {torch is not None}")
logger.info(f"Modelo carregado: {cls._initialized}")
logger.info(f"Classificação: {label} ({confidence:.2%})")
```

### Correção 5: Adicionar Modo de Fallback Total

**Permitir desabilitar OCR completamente:**
```python
# config.py
OCR_ENABLED = os.getenv('OCR_ENABLED', 'True').lower() == 'true'

# Se False, pular OCR totalmente
if not FinanceiroConfig.OCR_ENABLED:
    return {
        'ocr_status': 'disabled',
        'message': 'OCR desabilitado - preencha manualmente'
    }
```

---

## 📊 Checklist de Diagnóstico

### Configuração
- [ ] Arquivo de credenciais Google existe?
- [ ] Variável GOOGLE_APPLICATION_CREDENTIALS setada?
- [ ] API Google Vision habilitada no projeto?
- [ ] Conta Google tem créditos/billing ativo?
- [ ] PyTorch instalado? (`pip list | grep torch`)

### Quota e Limites
- [ ] Verificar contador de quota atual no banco
- [ ] Quota < 1000 este mês?
- [ ] Logs mostram erro de quota?

### Modelo PyTorch
- [ ] Arquivos do modelo existem (4 arquivos)?
- [ ] Modelo carrega sem erros?
- [ ] Acurácia de validação aceitável (>70%)?
- [ ] Dataset balanceado?
- [ ] Dataset grande o suficiente (>200 exemplos)?

### OCR
- [ ] Google Vision retorna texto?
- [ ] Fallback Tesseract funciona?
- [ ] Padrões regex extraem dados corretamente?
- [ ] Texto extraído tem qualidade suficiente?

### Associação de Dados
- [ ] Pagamentos têm pedido_id correto?
- [ ] Pedidos têm cliente_id correto?
- [ ] Relacionamentos estão íntegros?
- [ ] Arquivos salvos no diretório correto?

---

## 🎯 Plano de Ação Priorizado

### 🔴 URGENTE (Resolver AGORA)

#### 1. Verificar Configuração Google Vision
**Objetivo:** Confirmar se OCR principal está funcional

**Passos:**
1. Verificar se arquivo de credenciais existe
2. Testar conexão com API
3. Verificar quota atual no banco de dados
4. Analisar logs de erro recentes

**Comandos:**
```bash
# 1. Verificar arquivo
ls -la /Users/ericobrandao/keys/gvision-credentials.json

# 2. Testar conexão
python -c "from google.cloud import vision; vision.ImageAnnotatorClient()"

# 3. Ver quota
sqlite3 instance/sistema.db "SELECT * FROM ocr_quota WHERE ano=2025;"

# 4. Ver logs
tail -50 instance/logs/app.log | grep -i "ocr\|vision"
```

#### 2. Adicionar Logs Detalhados no OCR
**Objetivo:** Entender exatamente onde está falhando

**Arquivo:** `meu_app/financeiro/ocr_service.py`

**Adicionar:**
```python
def process_receipt(cls, file_path: str) -> dict:
    current_app.logger.info(f"[OCR] Iniciando processamento: {file_path}")
    
    # Verificar quota
    has_quota = cls._check_quota()
    current_app.logger.info(f"[OCR] Quota disponível: {has_quota}")
    
    # Tentar Vision
    try:
        result = VisionOcrService.extract_text(file_path)
        current_app.logger.info(f"[OCR] Vision OK. Texto: {len(result.get('text', ''))} chars")
    except Exception as e:
        current_app.logger.error(f"[OCR] Vision falhou: {str(e)}")
    
    # ... resto do código ...
```

#### 3. Criar Script de Teste Diagnóstico
**Arquivo:** `test_ocr_diagnostico.py` (novo)

```python
#!/usr/bin/env python3
"""Script de diagnóstico completo do OCR"""
import sys
import os

# Configurar app context
from meu_app import create_app
app = create_app()

with app.app_context():
    print("=" * 60)
    print("DIAGNÓSTICO OCR - MÓDULO FINANCEIRO")
    print("=" * 60)
    
    # 1. Verificar PyTorch
    print("\n1. PYTORCH:")
    try:
        import torch
        print(f"   ✅ Instalado: {torch.__version__}")
        from meu_app.financeiro.pytorch_validator import PaymentValidatorService
        result = PaymentValidatorService.evaluate_text("teste pix 150 reais")
        print(f"   ✅ Modelo funciona: {result.get('label')}")
        print(f"   Confiança: {result.get('confidence')}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 2. Verificar Google Vision
    print("\n2. GOOGLE VISION:")
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()
        print(f"   ✅ Cliente criado com sucesso")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 3. Verificar Quota
    print("\n3. QUOTA OCR:")
    try:
        from meu_app.models import OcrQuota
        from datetime import datetime
        quota = OcrQuota.query.filter_by(
            ano=datetime.now().year, 
            mes=datetime.now().month
        ).first()
        if quota:
            print(f"   Usado: {quota.contador}/1000")
            if quota.contador >= 1000:
                print(f"   ❌ QUOTA ESGOTADA!")
        else:
            print(f"   ✅ Nenhum uso este mês")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 4. Verificar Modelo PyTorch
    print("\n4. MODELO PYTORCH:")
    try:
        import json
        with open('models/pytorch_validator/training_report.json') as f:
            report = json.load(f)
        val_acc = report['val_metrics']['accuracy']
        print(f"   Acurácia validação: {val_acc:.1%}")
        if val_acc < 0.7:
            print(f"   ⚠️ MODELO MAL TREINADO! (< 70%)")
        dataset_size = sum(report['label_distribution'].values())
        print(f"   Tamanho dataset: {dataset_size} exemplos")
        if dataset_size < 100:
            print(f"   ⚠️ DATASET PEQUENO! (< 100)")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # 5. Testar OCR End-to-End
    print("\n5. TESTE OCR:")
    test_file = "uploads/recibos_pagamento_treinamento/pix_001.pdf"
    if os.path.exists(test_file):
        try:
            from meu_app.financeiro.ocr_service import OcrService
            result = OcrService.process_receipt(test_file)
            print(f"   Backend: {result.get('backend')}")
            print(f"   Valor: {result.get('amount')}")
            print(f"   ID: {result.get('transaction_id')}")
            print(f"   Erro: {result.get('error')}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    else:
        print(f"   ⚠️ Arquivo de teste não encontrado")
    
    print("\n" + "=" * 60)
    print("FIM DO DIAGNÓSTICO")
    print("=" * 60)
```

### Fase 2: Correções Baseadas no Diagnóstico

#### Correção A: Re-treinar Modelo PyTorch (Se necessário)

**Quando:** Se acurácia < 70% ou dataset < 100

**Passos:**
1. Coletar mais comprovantes reais (100+ por classe)
2. Balancear dataset
3. Ajustar hiperparâmetros:
   ```python
   epochs = 20
   learning_rate = 0.0001
   dropout = 0.5
   batch_size = 8
   early_stopping = 5
   ```
4. Re-treinar: `python scripts/train_pytorch_validator.py`
5. Validar métricas: val_acc > 70%

#### Correção B: Configurar Google Vision (Se necessário)

**Quando:** Se credenciais inválidas ou API não responde

**Passos:**
1. Obter credenciais válidas do Google Cloud Console
2. Salvar em `/Users/ericobrandao/keys/gvision-credentials.json`
3. Setar variável de ambiente:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/Users/ericobrandao/keys/gvision-credentials.json"
   ```
4. Habilitar API no projeto Google Cloud
5. Verificar billing ativo

#### Correção C: Melhorar Padrões Regex (Se necessário)

**Quando:** Se OCR extrai texto mas não encontra dados

**Arquivo:** `ocr_service.py`

**Melhorar padrões:**
```python
# Valor - mais flexível
VALOR_PATTERNS = [
    r'R?\$?\s*(\d{1,3}(?:\.\d{3})*,\d{2})',  # R$ 1.234,56
    r'valor[:\s]*R?\$?\s*(\d+[,\.]\d{2})',   # Valor: 123,45
    r'(\d+,\d{2})\s*(?:reais?|BRL)',         # 123,45 reais
]

# ID Transação - mais variações
ID_PATTERNS = [
    r'(?:ID|Código|Transação|Transaction)[:\s]*([A-Z0-9-]{6,})',
    r'(?:Ref|Referência)[:\s]*([A-Z0-9-]{6,})',
    r'E2E[:\s]*([A-Z0-9]{8,})',  # Chave E2E do PIX
]
```

#### Correção D: Resetar Quota (Se esgotada)

**Quando:** Se quota >= 1000

**SQL:**
```sql
-- Resetar quota do mês (apenas se autorizado)
UPDATE ocr_quota 
SET contador = 0 
WHERE ano = 2025 AND mes = 10;
```

**OU aumentar limite:**
```python
# config.py
OCR_MONTHLY_LIMIT = 5000  # Aumentar de 1000 para 5000
```

### Fase 3: Melhorias de Longo Prazo

#### Melhoria 1: Dashboard de Monitoramento OCR

**Criar página:** `/financeiro/ocr-stats`

**Mostrar:**
- Taxa de sucesso OCR (últimos 30 dias)
- Quota usada / disponível
- Tempo médio de processamento
- Backend usado (Vision vs Local)
- Erros comuns

#### Melhoria 2: Modo Manual Forçado

**Adicionar botão:**
```html
<button onclick="pularOCR()">⚠️ Pular OCR e Digitar Manualmente</button>
```

**Para quando:**
- OCR está falhando muito
- Usuário prefere digitar
- Documento ilegível

#### Melhoria 3: Validação Humana do PyTorch

**Quando modelo classifica como "suspeito":**
1. Salvar para revisão manual
2. Admin revisa e corrige label
3. Dados usados para re-treinar modelo
4. Melhoria contínua

---

## 📝 Relatório de Saída Esperado

Após executar o diagnóstico, teremos:

```
DIAGNÓSTICO OCR - MÓDULO FINANCEIRO
============================================================

1. PYTORCH:
   ✅ Instalado: 2.0.0
   ⚠️ Modelo funciona mas acurácia baixa (40%)
   ⚠️ Dataset pequeno (22 exemplos)
   
2. GOOGLE VISION:
   ❌ Erro: Credenciais inválidas
   → AÇÃO: Reconfigurar credenciais
   
3. QUOTA OCR:
   ⚠️ Usado: 1250/1000
   ❌ QUOTA ESGOTADA!
   → AÇÃO: Resetar quota ou aumentar limite
   
4. MODELO PYTORCH:
   ⚠️ Acurácia validação: 40% (PÉSSIMO)
   ⚠️ Dataset: 22 exemplos (INSUFICIENTE)
   → AÇÃO: Re-treinar com mais dados
   
5. TESTE OCR:
   ❌ Erro: Quota excedida
   → Backend: None
   → Fallback: Não executado
   
============================================================
RESUMO:
- Problemas encontrados: 3 críticos
- Re-treinar modelo: SIM
- Reconfigurar Vision: SIM
- Resetar quota: SIM
============================================================
```

---

## 🎯 Ordem de Execução Recomendada

### Passo 1: Diagnóstico (30 min)
1. Executar script de diagnóstico
2. Analisar logs
3. Identificar problema principal

### Passo 2: Quick Fixes (1 hora)
1. Resetar quota (se esgotada)
2. Configurar credenciais (se inválidas)
3. Adicionar logs detalhados

### Passo 3: Treinar Modelo (2-4 horas)
1. Coletar mais dados (100+ por classe)
2. Preparar dataset
3. Re-treinar modelo
4. Validar métricas

### Passo 4: Testes (30 min)
1. Testar OCR com arquivos reais
2. Verificar extração de dados
3. Validar classificação PyTorch
4. Confirmar salvamento correto

---

## 📈 Métricas de Sucesso

**Antes (Problemático):**
- OCR funciona: 30% das vezes
- Extração correta: 20% das vezes
- PyTorch acurácia: 40%
- Dataset: 22 exemplos

**Depois (Objetivo):**
- OCR funciona: 95% das vezes ✅
- Extração correta: 85% das vezes ✅
- PyTorch acurácia: 80%+ ✅
- Dataset: 200+ exemplos ✅

---

**Status:** Plano de diagnóstico completo - Aguardando aprovação para execução

