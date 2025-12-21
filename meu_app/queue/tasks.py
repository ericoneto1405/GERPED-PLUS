"""
Tasks assíncronas para processamento em background
"""

import os
from pathlib import Path
from typing import Dict, Optional

_flask_app = None


def _get_app():
    """
    Obtém (e cria, se necessário) a aplicação Flask para uso dentro do worker.
    """
    global _flask_app
    if _flask_app is None:
        from meu_app import create_app

        _flask_app = create_app()
    return _flask_app


def process_ocr_task(file_path: str, pedido_id: int, pagamento_id: Optional[int] = None) -> Dict:
    """
    Task assíncrona para processar OCR de comprovante
    
    Args:
        file_path: Caminho do arquivo PDF/imagem
        pedido_id: ID do pedido
        pagamento_id: ID do pagamento (opcional)
    
    Returns:
        Dict com resultado do OCR
    """
    from meu_app.financeiro.vision_service import VisionOcrService
    from rq import get_current_job
    
    job = get_current_job()
    
    try:
        # Atualizar progresso
        if job:
            job.meta['progress'] = 10
            job.meta['stage'] = 'Validando arquivo'
            job.save_meta()
        
        # Validar que arquivo existe
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        # Atualizar progresso
        if job:
            job.meta['progress'] = 30
            job.meta['stage'] = 'Processando OCR'
            job.save_meta()
        
        # Processar OCR
        result = VisionOcrService.process_receipt(file_path)
        
        # Atualizar progresso
        if job:
            job.meta['progress'] = 80
            job.meta['stage'] = 'Finalizando'
            job.save_meta()
        
        # Adicionar metadados
        result['pedido_id'] = pedido_id
        result['pagamento_id'] = pagamento_id
        result['file_path'] = file_path
        
        # Atualizar progresso
        if job:
            job.meta['progress'] = 100
            job.meta['stage'] = 'Concluído'
            job.save_meta()
        
        return {
            'success': True,
            'data': result
        }
        
    except Exception as e:
        # Log do erro
        error_msg = f"Erro no processamento OCR: {str(e)}"
        
        if job:
            job.meta['error'] = error_msg
            job.save_meta()
        
        return {
            'success': False,
            'error': error_msg,
            'pedido_id': pedido_id,
            'pagamento_id': pagamento_id
        }


def generate_receipt_task(coleta_data: Dict) -> Dict:
    """
    Task assíncrona para gerar recibo de coleta em imagem (JPG).
    
    Args:
        coleta_data: Dicionário com informações da coleta.
    
    Returns:
        Dict com resultado da geração.
    """
    from rq import get_current_job

    job = get_current_job()

    try:
        app = _get_app()

        with app.app_context():
            if job:
                job.meta['progress'] = 10
                job.meta['stage'] = 'Preparando documento'
                job.save_meta()

            from meu_app.coletas.receipt_service import ReceiptService

            pdf_path = ReceiptService.gerar_recibo_pdf(coleta_data)
            image_path = str(Path(pdf_path).with_suffix('.jpg'))

            if job:
                job.meta['progress'] = 100
                job.meta['stage'] = 'Concluído'
                job.save_meta()

            return {
                'success': True,
                'image_path': image_path,
                'pdf_path': pdf_path,
                'pedido_id': coleta_data.get('pedido_id'),
            }

    except Exception as exc:  # pragma: no cover - executa em worker externo
        error_msg = f"Erro na geração assíncrona de recibo: {exc}"

        if job:
            job.meta['error'] = error_msg
            job.save_meta()

        return {
            'success': False,
            'error': error_msg,
            'pedido_id': coleta_data.get('pedido_id'),
        }


def cleanup_receipts_task(ttl_hours: Optional[int] = None) -> Dict:
    """
    Remove recibos expirados conforme TTL configurado.
    """
    from rq import get_current_job

    job = get_current_job()

    try:
        if job:
            job.meta['progress'] = 5
            job.meta['stage'] = 'Iniciando limpeza de recibos'
            job.save_meta()

        app = _get_app()

        with app.app_context():
            from meu_app.coletas.receipt_service import ReceiptService

            removidos = ReceiptService.limpar_recibos_antigos(ttl_hours=ttl_hours)

            if job:
                job.meta['progress'] = 100
                job.meta['stage'] = 'Limpeza concluída'
                job.save_meta()

            return {
                'success': True,
                'removidos': removidos,
            }

    except Exception as exc:  # pragma: no cover
        error_msg = f"Erro ao limpar recibos expirados: {exc}"
        if job:
            job.meta['error'] = error_msg
            job.save_meta()
        return {
            'success': False,
            'error': error_msg,
        }
