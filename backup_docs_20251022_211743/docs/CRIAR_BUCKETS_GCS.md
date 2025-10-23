# 🪣 Criar Buckets GCS para OCR

## 📋 O Que Criar

Precisamos de **2 buckets** no Google Cloud Storage:

1. **`sap-ocr-input`** - Para PDFs enviados
2. **`sap-ocr-output`** - Para resultados do OCR

---

## 🚀 Método 1: Via gcloud CLI (Recomendado - 2 minutos)

### Passo 1: Verificar se gcloud está instalado

```bash
gcloud --version
```

**Se não estiver instalado**: https://cloud.google.com/sdk/docs/install

---

### Passo 2: Autenticar (se necessário)

```bash
# Definir projeto
gcloud config set project SEU_PROJECT_ID

# Autenticar
gcloud auth application-default login
```

---

### Passo 3: Criar os Buckets

```bash
# Bucket de entrada (PDFs originais)
gsutil mb -c STANDARD -l us-central1 gs://sap-ocr-input

# Bucket de saída (resultados OCR)
gsutil mb -c STANDARD -l us-central1 gs://sap-ocr-output
```

**Parâmetros**:
- `-c STANDARD`: Classe de storage (mais econômica)
- `-l us-central1`: Região (ajuste conforme necessário)

---

### Passo 4: Configurar Permissões

```bash
# Permitir que sua service account acesse os buckets
# (Substitua YOUR-SERVICE-ACCOUNT pelo email da sua service account)

gsutil iam ch serviceAccount:YOUR-SERVICE-ACCOUNT@YOUR-PROJECT.iam.gserviceaccount.com:objectAdmin gs://sap-ocr-input
gsutil iam ch serviceAccount:YOUR-SERVICE-ACCOUNT@YOUR-PROJECT.iam.gserviceaccount.com:objectAdmin gs://sap-ocr-output
```

**Como descobrir sua service account?**
```bash
cat /Users/ericobrandao/keys/gvision-credentials.json | grep client_email
```

---

### Passo 5: Verificar Criação

```bash
# Listar buckets
gsutil ls

# Verificar configuração
gsutil ls -L gs://sap-ocr-input
gsutil ls -L gs://sap-ocr-output
```

**Saída esperada**:
```
gs://sap-ocr-input/
gs://sap-ocr-output/
```

---

## 🌐 Método 2: Via Google Cloud Console (3 minutos)

### Passo 1: Acessar Console

1. Abra: https://console.cloud.google.com/storage
2. Selecione seu projeto

---

### Passo 2: Criar Bucket de Entrada

1. Clique em **"Criar Bucket"**
2. **Nome**: `sap-ocr-input`
3. **Região**: `us-central1` (ou sua preferência)
4. **Classe de storage**: Standard
5. **Controle de acesso**: Uniforme
6. Clique em **"Criar"**

---

### Passo 3: Criar Bucket de Saída

Repita o processo:
1. Clique em **"Criar Bucket"**
2. **Nome**: `sap-ocr-output`
3. **Região**: `us-central1` (mesma do anterior)
4. **Classe de storage**: Standard
5. **Controle de acesso**: Uniforme
6. Clique em **"Criar"**

---

### Passo 4: Configurar Permissões

Para cada bucket:

1. Clique no bucket
2. Aba **"Permissões"**
3. Clique **"Conceder Acesso"**
4. **Principais**: Email da sua service account
   - Ver em: `/Users/ericobrandao/keys/gvision-credentials.json` → `client_email`
5. **Papel**: `Storage Object Admin`
6. Clique em **"Salvar"**

---

## ✅ Após Criar os Buckets

### Teste 1: Verificar Buckets Existem

```bash
gsutil ls | grep sap-ocr
```

**Esperado**:
```
gs://sap-ocr-input/
gs://sap-ocr-output/
```

---

### Teste 2: Testar Upload Manual

```bash
# Criar arquivo de teste
echo "teste" > /tmp/teste.txt

# Upload para bucket
gsutil cp /tmp/teste.txt gs://sap-ocr-input/teste.txt

# Verificar
gsutil ls gs://sap-ocr-input/

# Limpar
gsutil rm gs://sap-ocr-input/teste.txt
```

**Se funcionar**: ✅ Buckets estão OK!

---

### Teste 3: Testar OCR com Seu PDF

```bash
cd /Users/ericobrandao/Projects/SAP

# Testar com seu arquivo
python test_ocr_direto.py "/Users/ericobrandao/Downloads/comp 1100.pdf"
```

**Esperado**:
```
✅ OCR EXECUTADO
💰 Valor encontrado: 1100.00
```

---

### Teste 4: Testar no Navegador Novamente

1. Reinicie o servidor (caso tenha parado)
2. Abra: http://localhost:5004/financeiro
3. Lançar pagamento em pedido pendente
4. Upload do mesmo PDF
5. **Agora deve funcionar!** ✅

---

## 🎯 Configuração Atual

Seu sistema está configurado assim:

```python
# meu_app/financeiro/config.py
GOOGLE_VISION_INPUT_BUCKET = 'sap-ocr-input'
GOOGLE_VISION_OUTPUT_BUCKET = 'sap-ocr-output'
```

**Você pode mudar os nomes** se preferir outros nomes de bucket.

---

## 💰 Custos

### Storage
- **Classe Standard**: ~$0.020/GB/mês
- **PDFs temporários**: Deletados após processamento
- **Custo típico**: < $1/mês para uso normal

### Google Vision
- **OCR**: Já está sendo usado (quota de 1000/mês)
- **Sem custo adicional** pelos buckets

---

## ⚠️ Importante

### Limpeza Automática

O sistema já limpa arquivos temporários:

```python
# meu_app/financeiro/vision_service.py
finally:
    cls._cleanup_gcs_resources(input_uri, output_uri)
```

### Segurança

- Buckets são **privados** (não públicos)
- Apenas sua service account tem acesso
- Arquivos são deletados após processamento

---

## 🐛 Se Algo Der Errado

### Erro: "Bucket name already exists"

Nomes de buckets são **globais** no GCS. Tente:
```bash
gsutil mb gs://sap-ocr-input-SEU-NOME
gsutil mb gs://sap-ocr-output-SEU-NOME
```

E atualize em `meu_app/financeiro/config.py`:
```python
GOOGLE_VISION_INPUT_BUCKET = 'sap-ocr-input-SEU-NOME'
GOOGLE_VISION_OUTPUT_BUCKET = 'sap-ocr-output-SEU-NOME'
```

---

### Erro: "Permission denied"

Sua service account precisa das permissões:
- `storage.buckets.create`
- `storage.objects.create`
- `storage.objects.delete`

Role recomendado: **Storage Object Admin**

---

## 📝 Checklist

- [ ] gcloud CLI instalado e configurado
- [ ] Projeto GCP selecionado
- [ ] Bucket `sap-ocr-input` criado
- [ ] Bucket `sap-ocr-output` criado
- [ ] Permissões configuradas
- [ ] Teste de upload manual OK
- [ ] Teste `python test_ocr_direto.py` OK
- [ ] Teste no navegador OK

---

**Crie os buckets e me avise quando estiver pronto para testar!** 🚀
