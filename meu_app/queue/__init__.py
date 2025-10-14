"""
Sistema de filas assíncronas com RQ (Redis Queue)
Fase 7 - Processamento assíncrono de OCR e uploads
"""

from redis import Redis
from rq import Queue
from flask import current_app

# Redis connection (singleton)
redis_conn = None
ocr_queue = None
pdf_queue = None


def init_queue(app):
    """
    Inicializa a conexão Redis e a fila RQ
    """
    global redis_conn, ocr_queue, pdf_queue
    
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    
    try:
        redis_conn = Redis.from_url(redis_url, decode_responses=True)
        redis_conn.ping()  # Testar conexão
        
        # Criar fila para OCR (com timeout de 5 minutos)
        ocr_queue = Queue('ocr', connection=redis_conn, default_timeout=300)
        pdf_queue = Queue('pdf', connection=redis_conn, default_timeout=600)
        
        app.logger.info(f"✅ RQ inicializado: {redis_url}")
        app.logger.info(f"✅ Fila 'ocr' criada com sucesso")
        app.logger.info("✅ Fila 'pdf' criada com sucesso")
        
    except Exception as e:
        app.logger.warning(f"⚠️ Redis não disponível: {e}")
        app.logger.warning("⚠️ Processamento OCR será SÍNCRONO")
        redis_conn = None
        ocr_queue = None
        pdf_queue = None


def get_queue():
    """Retorna a fila de OCR (ou None se Redis indisponível)"""
    return ocr_queue


def get_pdf_queue():
    """Retorna a fila de geração de PDF (ou None se indisponível)"""
    return pdf_queue


def get_redis():
    """Retorna a conexão Redis (ou None se indisponível)"""
    return redis_conn


def enqueue_ocr_job(file_path: str, pedido_id: int, pagamento_id: int = None):
    """
    Enfileira um job de OCR para processamento assíncrono
    
    Args:
        file_path: Caminho do arquivo a processar
        pedido_id: ID do pedido associado
        pagamento_id: ID do pagamento (opcional)
    
    Returns:
        Job ID ou None se fila indisponível
    """
    if ocr_queue is None:
        current_app.logger.warning("⚠️ Fila não disponível, processamento será síncrono")
        return None
    
    try:
        from .tasks import process_ocr_task
        
        job = ocr_queue.enqueue(
            process_ocr_task,
            file_path,
            pedido_id,
            pagamento_id,
            job_timeout=300,  # 5 minutos
            result_ttl=3600,  # Resultado expira em 1 hora
            failure_ttl=86400  # Falhas expiram em 24h
        )
        
        current_app.logger.info(f"✅ Job OCR enfileirado: {job.id}")
        return job.id
        
    except Exception as e:
        current_app.logger.error(f"❌ Erro ao enfileirar OCR: {e}")
        return None


def enqueue_pdf_job(coleta_data: dict):
    """
    Enfileira um job para geração assíncrona de recibo PDF
    
    Args:
        coleta_data: Dados necessários para gerar o recibo
    
    Returns:
        str | None: ID do job ou None se não foi possível enfileirar
    """
    if pdf_queue is None:
        current_app.logger.warning("⚠️ Fila de PDF indisponível, geração será síncrona")
        return None


def enqueue_receipt_cleanup_job(ttl_hours: int | None = None):
    """
    Enfileira uma tarefa para remover recibos expirados.
    """
    if pdf_queue is None:
        return None

    try:
        from .tasks import cleanup_receipts_task

        job = pdf_queue.enqueue(
            cleanup_receipts_task,
            ttl_hours,
            job_timeout=300,
            result_ttl=3600,
            failure_ttl=3600,
        )
        current_app.logger.debug(
            "Job de limpeza de recibos enfileirado",
            extra={"job_id": job.id, "ttl_horas": ttl_hours},
        )
        return job.id
    except Exception as exc:  # pragma: no cover
        current_app.logger.debug(
            "Falha ao enfileirar job de limpeza de recibos",
            exc_info=exc,
        )
        return None
    
    try:
        from .tasks import generate_receipt_task
        
        job = pdf_queue.enqueue(
            generate_receipt_task,
            coleta_data,
            job_timeout=600,
            result_ttl=86400,
            failure_ttl=86400,
        )
        current_app.logger.info(
            "✅ Job de recibo enfileirado",
            extra={
                "job_id": job.id,
                "pedido_id": coleta_data.get("pedido_id"),
            },
        )
        return job.id
    except Exception as e:
        current_app.logger.error(
            "❌ Erro ao enfileirar geração de recibo",
            exc_info=e,
            extra={"pedido_id": coleta_data.get("pedido_id")},
        )
        return None


def get_job_status(job_id: str):
    """
    Retorna o status de um job
    
    Returns:
        dict com status, progress, result ou error
    """
    if redis_conn is None:
        return {
            'status': 'unavailable',
            'message': 'Fila não disponível'
        }
    
    try:
        from rq.job import Job
        
        job = Job.fetch(job_id, connection=redis_conn)
        
        response = {
            'job_id': job.id,
            'status': job.get_status(),
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
        }
        
        # Status: queued, started, finished, failed
        meta = job.meta or {}

        if job.is_finished:
            response['result'] = job.result
            response['stage'] = meta.get('stage', 'Concluído')
        elif job.is_failed:
            response['error'] = str(job.exc_info)
            response['stage'] = meta.get('stage', 'Falha')
        elif job.is_started:
            response['progress'] = meta.get('progress', 0)
            response['stage'] = meta.get('stage', 'Processando')
        else:
            response['progress'] = meta.get('progress', 0)
            response['stage'] = meta.get('stage', 'Na fila')
        
        if meta.get('error') and 'error' not in response:
            response['error'] = meta.get('error')
        
        return response
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Erro ao buscar job: {str(e)}'
        }
