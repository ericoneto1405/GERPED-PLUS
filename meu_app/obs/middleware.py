"""
Middleware de Observabilidade
==============================

Middleware para rastreamento automático de requisições com logging e métricas.

Features:
- Request ID único para cada requisição
- Logging automático de início/fim de request
- Rastreamento de duração
- Correlação de logs via request_id
- Métricas automáticas de HTTP

Autor: Sistema GERPED
"""

import time
import uuid
from flask import g, request, current_app
from .metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress
)


def setup_request_tracking(app):
    """
    Configura middleware de rastreamento de requisições.
    
    Adiciona:
    - Request ID único
    - User ID (se autenticado)
    - Logging de início/fim
    - Métricas automáticas
    
    Args:
        app: Instância Flask
    """
    
    @app.before_request
    def before_request_handler():
        """Executado antes de cada requisição"""
        # Gerar ou usar request_id fornecido
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
        # Capturar user_id se usuário estiver logado
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            g.user_id = current_user.id
        else:
            g.user_id = None
        
        # Timestamp de início
        g.start_time = time.time()
        
        # Métricas: incrementar requests em andamento
        method = request.method
        endpoint = request.endpoint or 'unknown'
        http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint
        ).inc()
        
        # Log estruturado de início
        current_app.logger.info(
            'Request iniciado',
            extra={
                'event': 'request_started',
                'path': request.path,
                'query_string': request.query_string.decode('utf-8') if request.query_string else None,
                'user_agent': request.headers.get('User-Agent', 'unknown')
            }
        )
    
    @app.after_request
    def after_request_handler(response):
        """Executado após cada requisição bem-sucedida"""
        # Calcular duração
        duration = time.time() - g.get('start_time', time.time())
        
        # Adicionar request_id no header de resposta
        response.headers['X-Request-ID'] = g.get('request_id', 'unknown')
        
        # Métricas: decrementar requests em andamento
        method = request.method
        endpoint = request.endpoint or 'unknown'
        status = response.status_code
        
        http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint
        ).dec()
        
        # Métricas: registrar request completo
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        # Log estruturado de conclusão
        current_app.logger.info(
            'Request concluído',
            extra={
                'event': 'request_completed',
                'status_code': status,
                'duration_ms': round(duration * 1000, 2),
                'content_length': response.content_length or 0
            }
        )
        
        return response
    
    @app.teardown_request
    def teardown_request_handler(exception=None):
        """Executado sempre, mesmo se houver erro"""
        # Garantir que métricas de requests em andamento sejam decrementadas
        if hasattr(g, 'start_time'):
            method = request.method
            endpoint = request.endpoint or 'unknown'
            
            # Se houver exceção e métricas ainda não foram atualizadas
            if exception and http_requests_in_progress._metrics:
                try:
                    http_requests_in_progress.labels(
                        method=method,
                        endpoint=endpoint
                    ).dec()
                except Exception:
                    pass  # Evitar erros em cleanup
            
            # Log de exceção se houver
            if exception:
                duration = time.time() - g.start_time
                current_app.logger.error(
                    'Request falhou com exceção',
                    extra={
                        'event': 'request_failed',
                        'exception_type': type(exception).__name__,
                        'exception_message': str(exception),
                        'duration_ms': round(duration * 1000, 2)
                    },
                    exc_info=True
                )
    
    app.logger.info('Middleware de rastreamento de requisições inicializado')


def get_request_id():
    """
    Retorna o request_id da requisição atual.
    
    Returns:
        Request ID único da requisição
        
    Exemplo:
        >>> request_id = get_request_id()
        >>> logger.info(f"Processando request {request_id}")
    """
    return g.get('request_id', 'no-request-context')


def get_user_id():
    """
    Retorna o user_id da requisição atual (se autenticado).
    
    Returns:
        User ID ou None
    """
    return g.get('user_id')

