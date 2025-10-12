"""
Serviço de OCR simplificado - APENAS Google Vision.
"""
import os
import json
import hashlib
from datetime import datetime
from typing import Dict
from .config import FinanceiroConfig
from .exceptions import OcrProcessingError
from .vision_service import VisionOcrService
from .. import db
from ..models import OcrQuota

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
            now = datetime.now()
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
            now = datetime.now()
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

            result = {}
            if not use_local_only:
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

                # Usar APENAS Google Vision
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
