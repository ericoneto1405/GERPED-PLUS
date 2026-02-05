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
from .. import db
from ..models import OcrQuota
from ..time_utils import local_now_naive

class OcrService:
    """Serviço de OCR usando APENAS Google Vision API"""

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
    def _increment_quota(cls):
        """
        Incrementa o contador de quota para o mês atual.
        """
        if not FinanceiroConfig.is_ocr_limit_enforced():
            return
        
        try:
            now = local_now_naive()
            ano = now.year
            mes = now.month
            
            # Buscar ou criar quota do mês atual
            quota = OcrQuota.query.filter_by(ano=ano, mes=mes).first()
            
            if quota is None:
                quota = OcrQuota(ano=ano, mes=mes, contador=1)
                db.session.add(quota)
            else:
                quota.contador += 1
            
            db.session.commit()
            print(f"Quota OCR atualizada: {quota.contador}/{FinanceiroConfig.get_ocr_monthly_limit()}")
            
        except Exception as e:
            print(f"Erro ao incrementar quota OCR: {e}")

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
                        'backend': 'google_vision'
                    }

                # PDFs: obrigatoriamente converter para imagem antes do Vision
                if _is_pdf_file(original_path):
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
            result.setdefault('backend', 'google_vision')

            # Gravar cache
            if FinanceiroConfig.OCR_CACHE_ENABLED and sha256 and cache_path and not result.get('error'):
                try:
                    with open(cache_path, 'w', encoding='utf-8') as cf:
                        json.dump(result, cf, ensure_ascii=False)
                except Exception:
                    pass

            # Incrementar quota após processamento bem-sucedido
            if not result.get('error') and result.get('fallback_used') is not True and not use_local_only:
                cls._increment_quota()

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
