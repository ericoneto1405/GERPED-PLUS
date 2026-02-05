#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path
from importlib.util import find_spec


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def has_module(name: str) -> bool:
    return find_spec(name) is not None


def status(label: str, ok: bool, details: str = "") -> None:
    prefix = "OK" if ok else "FALHOU"
    line = f"- {label}: {prefix}"
    if details:
        line += f" ({details})"
    print(line)


def header(title: str) -> None:
    print("\n" + title)
    print("-" * len(title))


def main() -> int:
    print("Teste rápido OCR + ML (smoke test)")
    print("Observação: não faz OCR real; só valida preparação do ambiente.")

    # OCR
    header("OCR")
    ocr_remote_ok = False
    ocr_remote_details = []

    vision_lib_ok = has_module("google.cloud.vision")
    status("google-cloud-vision instalado", vision_lib_ok)

    api_key = os.getenv("GOOGLE_VISION_API_KEY") or os.getenv("GOOGLE_API_KEY")
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("FINANCEIRO_GVISION_CREDENTIALS_PATH")
    cred_exists = bool(cred_path and Path(cred_path).exists())

    status("API Key configurada", bool(api_key))
    status("Credenciais (arquivo) configuradas", cred_exists, cred_path or "")

    local_only = os.getenv("FINANCEIRO_OCR_LOCAL_ONLY", "False").lower() == "true"
    status("OCR remoto desabilitado (modo local apenas)", local_only)

    fitz_ok = has_module("fitz")
    status("PyMuPDF (fitz) instalado", fitz_ok)

    # Fallback local
    header("OCR local (fallback)")
    status("Pillow instalado", has_module("PIL"))
    status("pytesseract instalado", has_module("pytesseract"))
    status("PyPDF2/pypdf instalado", has_module("PyPDF2") or has_module("pypdf"))
    status("pdfminer.six instalado", has_module("pdfminer"))

    # Teste de inicialização do cliente OCR remoto
    if vision_lib_ok and not local_only and (api_key or cred_exists):
        try:
            from flask import Flask
            app = Flask("ocr_smoke")
            app.root_path = str(ROOT / "meu_app")
            with app.app_context():
                from meu_app.financeiro.vision_service import VisionOcrService
                VisionOcrService._get_client()
            ocr_remote_ok = True
        except Exception as exc:
            ocr_remote_details.append(str(exc))
            ocr_remote_ok = False
    else:
        if local_only:
            ocr_remote_details.append("OCR remoto desabilitado por FINANCEIRO_OCR_LOCAL_ONLY.")
        elif not (api_key or cred_exists):
            ocr_remote_details.append("Sem API Key ou credenciais.")
        elif not vision_lib_ok:
            ocr_remote_details.append("Biblioteca google-cloud-vision ausente.")

    status("OCR remoto pronto para uso", ocr_remote_ok, "; ".join(ocr_remote_details))

    if api_key and not cred_exists:
        print("Aviso: API Key atende imagens, mas PDFs exigem credenciais de serviço.")

    # ML
    header("ML (validador PyTorch)")
    torch_ok = has_module("torch")
    status("PyTorch instalado", torch_ok)

    model_dir = ROOT / "models" / "pytorch_validator"
    model_files_ok = all((model_dir / name).exists() for name in ("payment_validator.pt", "vocab.json", "labels.json"))
    status("Arquivos do modelo encontrados", model_files_ok, str(model_dir))

    ml_ok = False
    ml_details = []
    if torch_ok and model_files_ok:
        try:
            from flask import Flask
            app = Flask("ml_smoke")
            app.root_path = str(ROOT / "meu_app")
            app.config["PAYMENT_VALIDATOR_DIR"] = str(model_dir)
            with app.app_context():
                from meu_app.financeiro.pytorch_validator import PaymentValidatorService
                result = PaymentValidatorService.evaluate_text("comprovante pix transferencia banco")
            if result.get("error"):
                ml_ok = False
                ml_details.append(result["error"])
            else:
                ml_ok = True
        except Exception as exc:
            ml_ok = False
            ml_details.append(str(exc))
    else:
        if not torch_ok:
            ml_details.append("PyTorch não instalado.")
        if not model_files_ok:
            ml_details.append("Arquivos do modelo ausentes.")

    status("ML pronto para uso", ml_ok, "; ".join(ml_details))

    print("\nResumo:")
    print(f"- OCR remoto: {'OK' if ocr_remote_ok else 'NÃO OK'}")
    print(f"- ML: {'OK' if ml_ok else 'NÃO OK'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
