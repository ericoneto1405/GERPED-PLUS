"""
OCR usando OCR.Space (https://ocr.space/).

Objetivo: oferecer um provider temporário enquanto o Google Vision não está configurado.
Retorna apenas o texto bruto; a extração de valor/ID/data reutiliza as rotinas já existentes.
"""

from __future__ import annotations

import os
from typing import Optional, Dict

import requests

from .exceptions import OcrProcessingError


class OcrSpaceService:
    _endpoint = "https://api.ocr.space/parse/image"

    @staticmethod
    def get_api_key() -> Optional[str]:
        return (
            os.getenv("FINANCEIRO_OCR_SPACE_API_KEY")
            or os.getenv("OCR_SPACE_API_KEY")
        )

    @classmethod
    def extract_text(cls, file_path: str) -> str:
        api_key = cls.get_api_key()
        if not api_key:
            raise OcrProcessingError(
                "OCR.Space não configurado. Defina FINANCEIRO_OCR_SPACE_API_KEY (ou OCR_SPACE_API_KEY)."
            )
        if not os.path.exists(file_path):
            raise OcrProcessingError("Arquivo não encontrado para OCR.")

        try:
            with open(file_path, "rb") as fh:
                files = {"file": fh}
                data = {
                    "apikey": api_key,
                    # Português (melhor para comprovantes BR).
                    "language": "por",
                    # Não precisamos de overlay/coords nesse fluxo.
                    "isOverlayRequired": "false",
                    # Melhor para documentos (comprovantes) do que apenas "normal".
                    "OCREngine": "2",
                    # Deixar o próprio provider detectar.
                    "detectOrientation": "true",
                }
                resp = requests.post(
                    cls._endpoint,
                    files=files,
                    data=data,
                    timeout=120,
                )
        except requests.RequestException as exc:
            raise OcrProcessingError(f"Falha ao chamar OCR.Space: {exc}") from exc

        if resp.status_code >= 400:
            raise OcrProcessingError(
                f"OCR.Space retornou HTTP {resp.status_code}. Tente novamente."
            )

        try:
            payload: Dict = resp.json()
        except Exception as exc:
            raise OcrProcessingError("Resposta inválida do OCR.Space (não é JSON).") from exc

        # Formato típico:
        # { "OCRExitCode": 1, "IsErroredOnProcessing": false, "ParsedResults":[{"ParsedText":"..."}], "ErrorMessage":null }
        if payload.get("IsErroredOnProcessing") is True:
            msg = payload.get("ErrorMessage") or payload.get("ErrorDetails") or "Erro no OCR.Space."
            if isinstance(msg, list):
                msg = "; ".join(str(x) for x in msg if x)
            raise OcrProcessingError(str(msg))

        parsed = payload.get("ParsedResults") or []
        texts = []
        for item in parsed:
            t = (item or {}).get("ParsedText")
            if t:
                texts.append(t)
        return ("\n".join(texts)).strip()

