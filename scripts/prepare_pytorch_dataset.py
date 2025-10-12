"""
Gera um dataset estruturado para treinamento PyTorch a partir dos comprovantes rotulados.

Fluxo:
1. Lê o CSV de rótulos (docs/comprovantes_rotulos_template.csv).
2. Para cada linha, localiza o arquivo dentro de uploads/recibos_pagamento_treinamento/.
3. Usa o serviço Google Vision para extrair o texto completo do comprovante.
4. Salva os resultados em data/comprovantes_dataset.jsonl com os campos:
   - arquivo
   - texto_ocr (ou null se ocorrer erro)
   - valor_pago
   - pix_recebedor
   - cnpj_recebedor
   - id_transacao
   - status_observacao
   - ocr_backend (documentação)
   - ocr_error (quando aplicável)

Pré-requisitos:
- GOOGLE_VISION_CREDENTIALS_PATH configurado em meu_app/financeiro/config.py.
- Credenciais válidas e dependências google-cloud-vision/storage instaladas.
- A pasta uploads/recibos_pagamento_treinamento/ contendo os arquivos indicados no CSV.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict

from meu_app.financeiro.vision_service import VisionOcrService

ROOT_DIR = Path(__file__).resolve().parents[1]
LABELS_CSV = ROOT_DIR / "docs" / "comprovantes_rotulos_template.csv"
DATASET_OUTPUT = ROOT_DIR / "data" / "comprovantes_dataset.jsonl"
TRAINING_FILES_DIR = ROOT_DIR / "uploads" / "recibos_pagamento_treinamento"


def extract_text(file_path: Path) -> Dict[str, Any]:
    """Executa a extração de texto via Google Vision, retornando dados e eventuais erros."""
    try:
        texto = VisionOcrService.extract_text(str(file_path))
        return {
            "texto_ocr": texto,
            "ocr_backend": "google_vision",
            "ocr_error": None,
        }
    except Exception as exc:  # noqa: BLE001 - precisamos retornar o erro ao chamador
        return {
            "texto_ocr": None,
            "ocr_backend": "google_vision",
            "ocr_error": str(exc),
        }


def build_record(row: Dict[str, str]) -> Dict[str, Any]:
    """Constrói o dicionário de saída para uma linha do CSV."""
    filename = row.get("arquivo", "").strip()
    if not filename:
        raise ValueError("Linha do CSV sem valor na coluna 'arquivo'.")

    file_path = TRAINING_FILES_DIR / filename
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo '{filename}' não encontrado em {TRAINING_FILES_DIR}.")

    ocr_data = extract_text(file_path)

    return {
        "arquivo": filename,
        "texto_ocr": ocr_data["texto_ocr"],
        "valor_pago": row.get("valor_pago", "").strip() or None,
        "pix_recebedor": row.get("pix_recebedor ", "").strip() or None,
        "cnpj_recebedor": row.get("cnpj_recebedor", "").strip() or None,
        "id_transacao": row.get(" id_transacao ", "").strip() or None,
        "status_observacao": row.get("status_observacao", "").strip() or None,
        "ocr_backend": ocr_data["ocr_backend"],
        "ocr_error": ocr_data["ocr_error"],
    }


def main() -> int:
    if not LABELS_CSV.exists():
        print(f"Arquivo de rótulos não encontrado: {LABELS_CSV}", file=sys.stderr)
        return 1

    if not TRAINING_FILES_DIR.exists():
        print(f"Pasta de comprovantes não encontrada: {TRAINING_FILES_DIR}", file=sys.stderr)
        return 1

    DATASET_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with LABELS_CSV.open("r", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")
        if reader.fieldnames is None:
            print("CSV de rótulos está vazio ou sem cabeçalho.", file=sys.stderr)
            return 1

        records = []
        for idx, row in enumerate(reader, start=1):
            filename = (row.get("arquivo") or "").strip()
            if not filename:
                print(f"[aviso] Linha {idx} ignorada (coluna 'arquivo' vazia).", file=sys.stderr)
                continue

            try:
                record = build_record(row)
                records.append(record)
                status = "ok" if record["ocr_error"] is None else "erro_ocr"
                print(f"[{status}] {filename}")
            except Exception as exc:  # noqa: BLE001
                print(f"[falha] {filename}: {exc}", file=sys.stderr)

    if not records:
        print("Nenhum registro processado com sucesso.", file=sys.stderr)
        return 1

    with DATASET_OUTPUT.open("w", encoding="utf-8") as dataset_file:
        for record in records:
            dataset_file.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nDataset gerado em: {DATASET_OUTPUT}")
    print("Formato: JSON Lines (um objeto por linha).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
