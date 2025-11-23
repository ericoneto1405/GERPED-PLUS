"""
Fallback local de OCR quando o Google Vision não está acessível.

Estratégia:
- Para arquivos de texto simples, tenta leitura direta.
- Para PDFs, tenta usar PyPDF2 ou pdfminer (se disponíveis).
- Para imagens, tenta usar Pillow + pytesseract (se instalados).
- Caso nenhuma extração funcione, retorna None.
"""
from __future__ import annotations

import os
import re
from typing import Optional, Dict


class LocalOcrFallback:
    """Fallback simples para tentativa de extração local de dados do comprovante."""

    TEXT_EXTENSIONS = {'.txt', '.log', '.csv'}
    PDF_EXTENSIONS = {'.pdf'}
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff'}

    @classmethod
    def process(cls, file_path: str) -> Optional[Dict]:
        """
        Tenta extrair informações básicas do comprovante usando processamento local.

        Returns:
            Dict com as mesmas chaves retornadas pelo OCR principal em caso de sucesso.
        """
        text = cls._extract_text(file_path)
        if not text:
            return None

        from .vision_service import VisionOcrService  # import lazily para evitar ciclos
        from .config import FinanceiroConfig

        amount = VisionOcrService._find_amount_in_text(text)
        transaction_id = VisionOcrService._find_transaction_id_in_text(text)
        date = VisionOcrService._find_date_in_text(text)
        bank_info = VisionOcrService._find_bank_info_in_text(text)

        validacao_recebedor = None
        if FinanceiroConfig.validar_recebedor_habilitado():
            recebedor_esperado = FinanceiroConfig.get_recebedor_esperado()
            validacao_recebedor = VisionOcrService._validar_recebedor(bank_info, recebedor_esperado)

        return {
            'amount': amount,
            'transaction_id': transaction_id,
            'date': date,
            'bank_info': bank_info,
            'validacao_recebedor': validacao_recebedor,
            'error': None,
            'fallback_used': True,
            'backend': 'local_fallback',
            'raw_text': text,
        }

    @classmethod
    def _extract_text(cls, file_path: str) -> Optional[str]:
        ext = os.path.splitext(file_path)[1].lower()

        if ext in cls.TEXT_EXTENSIONS:
            return cls._read_text_file(file_path)

        if ext in cls.PDF_EXTENSIONS:
            text = cls._read_pdf(file_path)
            if text:
                return text

        if ext in cls.IMAGE_EXTENSIONS:
            text = cls._read_image(file_path)
            if text:
                return text

        # Tentativa genérica: tentar decodificar como texto
        return cls._read_binary_as_text(file_path)

    @staticmethod
    def _read_text_file(file_path: str) -> Optional[str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as fh:
                return fh.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as fh:
                    return fh.read()
            except Exception:
                return None
        except Exception:
            return None

    @staticmethod
    def _read_pdf(file_path: str) -> Optional[str]:
        # 0) PyMuPDF (fitz) - mais resiliente que poppler para PDFs de banco
        try:
            import fitz  # type: ignore

            with fitz.open(file_path) as doc:
                texts = []
                for page in doc:
                    content = page.get_text("text") or ""
                    if content.strip():
                        texts.append(content)
                if texts:
                    combined = "\n".join(texts).strip()
                    if combined:
                        return combined
        except Exception:
            pass

        # 1) PyPDF (novo nome do PyPDF2)
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                extracted = page.extract_text() or ''
                if extracted:
                    text_parts.append(extracted)
            if text_parts:
                return '\n'.join(text_parts)
        except Exception:
            pass

        # 2) pdfminer.six
        try:
            from pdfminer.high_level import extract_text  # type: ignore

            text = extract_text(file_path)
            if text:
                return text
        except Exception:
            pass

        return None

    @staticmethod
    def _read_image(file_path: str) -> Optional[str]:
        try:
            from PIL import Image  # type: ignore
            import pytesseract  # type: ignore

            with Image.open(file_path) as img:
                # Melhorar contraste básico antes do OCR
                if img.mode not in ('L', 'RGB'):
                    img = img.convert('RGB')
                text = pytesseract.image_to_string(img, lang='por+eng')
                text = text.strip()
                if text:
                    return text
        except Exception:
            pass

        return None

    @staticmethod
    def _read_binary_as_text(file_path: str) -> Optional[str]:
        try:
            with open(file_path, 'rb') as fh:
                raw = fh.read()
            # Se parecer claramente um PDF binário, não usar como texto
            if raw.startswith(b'%PDF'):
                return None

            text = raw.decode('utf-8', errors='ignore')
            text = re.sub(r'\s+', ' ', text)
            # Heurística simples: descartar se a maior parte é não-imprimível
            printable = sum(1 for ch in text if 32 <= ord(ch) < 127)
            if len(text) == 0 or printable / max(len(text), 1) < 0.7:
                return None
            return text if text.strip() else None
        except Exception:
            return None
