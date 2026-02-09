"""
Serviço de OCR simplificado - APENAS Google Vision.
"""
import os
import json
import hashlib
from typing import Dict, Optional
import uuid
from flask import current_app
from .config import FinanceiroConfig
from .exceptions import OcrProcessingError
from .vision_service import VisionOcrService
from .ocr_space_service import OcrSpaceService
from .. import db
from ..models import OcrQuota
from ..time_utils import local_now_naive

class OcrService:
    """Serviço de OCR usando APENAS Google Vision API"""

    @classmethod
    def _is_google_configured(cls) -> bool:
        api_key = FinanceiroConfig.get_google_api_key()
        credentials_path = FinanceiroConfig.get_google_credentials_path()
        if api_key:
            return True
        if credentials_path and os.path.exists(credentials_path):
            return True
        return False

    @classmethod
    def _should_use_ocr_space(cls) -> bool:
        provider = (FinanceiroConfig.get_ocr_provider() or "google").strip().lower()
        if provider == "ocr_space":
            return True
        return False

    @classmethod
    def _check_quota(cls) -> bool:
        """
        Verifica se ainda há quota disponível para OCR no mês atual.
        Returns:
            bool: True se há quota disponível, False se atingiu o limite
        """
        if not FinanceiroConfig.is_ocr_limit_enforced():
            return True
        
        try:
            now = local_now_naive()
            ano = now.year
            mes = now.month
            
            # Buscar quota do mês atual
            quota = OcrQuota.query.filter_by(ano=ano, mes=mes).first()
            
            if quota is None:
                # Criar nova quota para o mês
                quota = OcrQuota(ano=ano, mes=mes, contador=0)
                db.session.add(quota)
                db.session.commit()
            
            # Verificar se atingiu o limite
            limite = FinanceiroConfig.get_ocr_monthly_limit()
            if quota.contador >= limite:
                return False
            
            return True
            
        except Exception as e:
            print(f"Erro ao verificar quota OCR: {e}")
            # Em caso de erro, permitir o processamento
            return True
    
    @classmethod
    def _reserve_quota(cls) -> bool:
        """
        Reserva 1 unidade da quota para o mês atual.

        Motivo: o Google pode cobrar uma chamada mesmo quando ela falha, então contar
        apenas "sucessos" pode deixar o contador interno menor que o consumo real.
        Este método reserva a cota antes de chamar o provider remoto.
        """
        if not FinanceiroConfig.is_ocr_limit_enforced():
            return True
        
        try:
            now = local_now_naive()
            ano = now.year
            mes = now.month
            
            # Buscar ou criar quota do mês atual
            quota = OcrQuota.query.filter_by(ano=ano, mes=mes).first()
            
            if quota is None:
                quota = OcrQuota(ano=ano, mes=mes, contador=0)
                db.session.add(quota)

            limite = FinanceiroConfig.get_ocr_monthly_limit()
            if quota.contador >= limite:
                try:
                    db.session.rollback()
                except Exception:
                    pass
                return False

            quota.contador += 1
            db.session.commit()
            try:
                current_app.logger.info(
                    f"OCR: quota reservada {quota.contador}/{limite} para {mes:02d}/{ano}"
                )
            except Exception:
                print(f"OCR: quota reservada {quota.contador}/{limite} para {mes:02d}/{ano}")
            return True

        except Exception as e:
            try:
                db.session.rollback()
            except Exception:
                pass
            print(f"Erro ao reservar quota OCR: {e}")
            # Em caso de erro, permitir o processamento (fail-open)
            return True

    @classmethod
    def process_receipt(cls, file_path: str) -> dict:
        """
        Processa um arquivo de recibo usando APENAS Google Vision.
        Retorna um dicionário com todos os dados encontrados.
        """

        def _convert_pdf_to_image(pdf_path: str) -> Optional[str]:
            """Converte a primeira página do PDF em imagem temporária."""
            temp_dir = FinanceiroConfig.get_upload_directory('temp')
            os.makedirs(temp_dir, exist_ok=True)
            output_path = os.path.join(temp_dir, f"ocr_pdf_page_{uuid.uuid4().hex}.png")

            def _log_warning(msg: str):
                try:
                    if current_app:
                        current_app.logger.warning(msg)
                        return
                except Exception:
                    pass
                print(msg)

            def _log_info(msg: str):
                try:
                    if current_app:
                        current_app.logger.info(msg)
                        return
                except Exception:
                    pass
                print(msg)

            # Tentativa 0: garantir remoção de arquivo antigo, se existir
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception:
                pass

            # Tentativa 1: PyMuPDF (FitZ) - mais robusto para PDFs de bancos
            try:
                import fitz  # PyMuPDF

                with fitz.open(pdf_path) as doc:
                    if doc.page_count == 0:
                        return None
                    page = doc.load_page(0)
                    # matrix para 300 DPI
                    zoom = 300 / 72
                    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB, alpha=False)
                    pix.save(output_path)
                # Validação básica da imagem gerada
                from PIL import Image  # import local para evitar custo em outros caminhos
                with Image.open(output_path) as img:
                    img.verify()
                _log_info(f"OCR: PDF convertido com PyMuPDF para {output_path} (size={os.path.getsize(output_path)} bytes)")
                return output_path
            except ModuleNotFoundError:
                _log_warning(
                    "PyMuPDF (fitz) não está instalado. Instale com 'pip install PyMuPDF' ou configure FINANCEIRO_GVISION_CREDENTIALS_PATH para permitir o envio direto do PDF ao Vision."
                )
            except Exception as exc:
                _log_warning(f"PyMuPDF falhou na conversão PDF->imagem: {exc}")

            return None

        def _is_pdf_file(path: str) -> bool:
            """Detecta PDFs mesmo quando a extensão foi perdida."""
            if path.lower().endswith('.pdf'):
                return True
            try:
                with open(path, 'rb') as fh:
                    header = fh.read(5)
                return header.startswith(b'%PDF')
            except Exception:
                return False

        try:
            # Cache por SHA-256 do arquivo
            cache_dir = os.path.join(FinanceiroConfig.get_upload_directory('temp'), '..', '.ocr_cache')
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except Exception:
                pass

            sha256 = None
            try:
                with open(file_path, 'rb') as f:
                    file_bytes = f.read()
                sha256 = hashlib.sha256(file_bytes).hexdigest()
            except Exception:
                sha256 = None

            cache_path = os.path.join(cache_dir, f"{sha256}.json") if sha256 else None

            # Verificar cache primeiro (não conta na quota)
            if FinanceiroConfig.OCR_CACHE_ENABLED and sha256 and os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as cf:
                        cached_result = json.load(cf)
                    # Evitar perpetuar respostas com erro genérico que podem ser transitórias
                    if cached_result.get('error'):
                        os.remove(cache_path)
                    else:
                        return cached_result
                except Exception:
                    pass

            use_local_only = FinanceiroConfig.use_local_ocr_only()
            original_path = file_path

            result = {}
            if not use_local_only:
                use_ocr_space = cls._should_use_ocr_space()
                if not use_ocr_space and not cls._is_google_configured():
                    return {
                        'amount': None,
                        'transaction_id': None,
                        'date': None,
                        'bank_info': {},
                        'error': (
                            'Credenciais do Google Vision não configuradas. '
                            'Defina GOOGLE_VISION_API_KEY ou GOOGLE_APPLICATION_CREDENTIALS/FINANCEIRO_GVISION_CREDENTIALS_PATH, '
                            'ou configure FINANCEIRO_OCR_PROVIDER=ocr_space com FINANCEIRO_OCR_SPACE_API_KEY.'
                        ),
                        'backend': 'google_vision'
                    }

                try:
                    current_app.logger.info(f"OCR: iniciando processamento - file={file_path}, sha256={sha256}")
                except Exception:
                    pass

                # Verificar quota antes de processar (só conta em cache miss)
                if not cls._check_quota():
                    return {
                        'amount': None,
                        'transaction_id': None,
                        'date': None,
                        'bank_info': {},
                        'error': f'Limite mensal de OCR atingido ({FinanceiroConfig.get_ocr_monthly_limit()} chamadas). Tente novamente no próximo mês.',
                        'backend': 'ocr'
                    }

                # PDFs: obrigatoriamente converter para imagem antes do Vision
                # Para Google Vision: convertemos PDF->imagem para reduzir variações.
                # Para OCR.Space: ele aceita PDF diretamente; não convertemos aqui.
                if not use_ocr_space and _is_pdf_file(original_path):
                    image_path = _convert_pdf_to_image(original_path)
                    if image_path:
                        file_path = image_path
                        try:
                            current_app.logger.info(f"OCR: imagem gerada para Vision: {file_path}")
                        except Exception:
                            pass
                    else:
                        return {
                            'amount': None,
                            'transaction_id': None,
                            'date': None,
                            'bank_info': {},
                            'error': (
                                'Falha ao converter PDF para imagem. '
                                'Verifique se PyMuPDF está instalado e se o arquivo não está corrompido.'
                            ),
                            'backend': 'google_vision'
                        }

                # Reserva a quota imediatamente antes da chamada ao provider remoto.
                # Assim, evitamos que chamadas cobradas pelo Google fiquem "sem contagem" local.
                if not cls._reserve_quota():
                    return {
                        'amount': None,
                        'transaction_id': None,
                        'date': None,
                        'bank_info': {},
                        'error': f'Limite mensal de OCR atingido ({FinanceiroConfig.get_ocr_monthly_limit()} chamadas). Tente novamente no próximo mês.',
                        'backend': 'ocr'
                    }

                if use_ocr_space:
                    text = OcrSpaceService.extract_text(file_path)
                    # Reutiliza as rotinas de parsing do VisionOcrService (sem chamar o Google).
                    amount = VisionOcrService._find_amount_in_text(text)  # type: ignore[attr-defined]
                    transaction_id = VisionOcrService._find_transaction_id_in_text(text)  # type: ignore[attr-defined]
                    date = VisionOcrService._find_date_in_text(text)  # type: ignore[attr-defined]
                    bank_info = VisionOcrService._find_bank_info_in_text(text)  # type: ignore[attr-defined]
                    validacao_recebedor = None
                    try:
                        if FinanceiroConfig.validar_recebedor_habilitado():
                            recebedor_esperado = FinanceiroConfig.get_recebedor_esperado()
                            validacao_recebedor = VisionOcrService._validar_recebedor(bank_info, recebedor_esperado)  # type: ignore[attr-defined]
                    except Exception:
                        validacao_recebedor = None

                    result = {
                        'amount': amount,
                        'transaction_id': transaction_id,
                        'date': date,
                        'bank_info': bank_info,
                        'validacao_recebedor': validacao_recebedor,
                        'backend': 'ocr_space',
                        'raw_text': text,
                    }
                else:
                    result = VisionOcrService.process_receipt(file_path)
            else:
                result = {
                    'amount': None,
                    'transaction_id': None,
                    'date': None,
                    'bank_info': {},
                    'error': 'OCR remoto desabilitado neste ambiente.',
                    'backend': 'google_vision_disabled'
                }

            result['bank_info'] = result.get('bank_info') or {}
            result.setdefault('fallback_used', False)
            result.setdefault('backend', 'ocr')

            # Gravar cache
            if FinanceiroConfig.OCR_CACHE_ENABLED and sha256 and cache_path and not result.get('error'):
                try:
                    with open(cache_path, 'w', encoding='utf-8') as cf:
                        json.dump(result, cf, ensure_ascii=False)
                except Exception:
                    pass

            return result
            
        except OcrProcessingError as e:
            return {
                'amount': None, 
                'transaction_id': None,
                'date': None,
                'bank_info': {},
                'error': str(e)
            }
        except Exception as e:
            return {
                'amount': None, 
                'transaction_id': None,
                'date': None,
                'bank_info': {},
                'error': f'Erro inesperado no OCR: {str(e)}'
            }
