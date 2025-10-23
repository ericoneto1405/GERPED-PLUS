# Integração do modelo PyTorch na validação de comprovantes

Este roteiro descreve como acoplar o classificador treinado (`scripts/train_pytorch_validator.py`) ao fluxo existente de OCR (`financeiro.processar_recibo_ocr`).

## 1. Carregamento do modelo
- Criar um módulo utilitário, por exemplo `meu_app/financeiro/pytorch_validator.py`, responsável por:
  - Ler `models/pytorch_validator/payment_validator.pt`.
  - Carregar `vocab.json` e `labels.json`.
  - Instanciar `ValidatorNet` com os mesmos parâmetros usados no treino.
  - Manter o modelo e o vocabulário como singletons (lazy load) para evitar custo por requisição.

## 2. Pré-processamento do texto
- Reutilizar a mesma tokenização (`\b\w+\b`, lower) para garantir compatibilidade.
- Converter o texto OCR em vetor bag-of-words com base no `vocab.json`.
  - Tokens não vistos devem ser ignorados (mesmo comportamento do treino).

## 3. Execução do classificador
- Gerar logits e aplicar `softmax` para obter probabilidades por classe.
- Mapear os índices de volta para labels usando `labels.json`.
- Sugerir um score principal:
  - `label_predita`: classe de maior probabilidade.
  - `confianca`: probabilidade associada (0-1).
  - Pode-se calcular uma flag binária (`suspeito`/`invalido`) para simplificar regras de negócio.

## 4. Enriquecimento da resposta OCR
- Após `OcrService.process_receipt`, chamar o validador com `texto_ocr` completo.
- Incluir os campos no JSON retornado ao frontend, por exemplo:
  ```json
  {
    "ml_status": "invalido",
    "ml_confidence": 0.82,
    "ml_scores": {"invalido": 0.82, "valido": 0.15, "suspeito": 0.03}
  }
  ```
- Frontend pode exibir alerta conforme `ml_status` e `ml_confidence`.

## 5. Rotina de inferência e dependências
- Certificar-se de que `torch` está disponível no ambiente de produção.
- Em caso de indisponibilidade do modelo (arquivos ausentes ou erro de carregamento):
  - Retornar campos `ml_status=None`, `ml_error` explicando o motivo.
  - Não bloquear o fluxo principal de registro de pagamentos.

## 6. Manutenção e re-treino
- Sempre gerar `data/comprovantes_dataset.jsonl` atualizado antes de rodar `scripts/train_pytorch_validator.py`.
- Convention: salvar novos modelos em versões (`models/pytorch_validator/v1/...`) se desejar controle histórico.
- Documentar métricas relevantes no `training_report.json` para auditoria.

Com esses passos, o classificador PyTorch passa a reforçar a validação dos comprovantes logo após a extração via Google Vision.
