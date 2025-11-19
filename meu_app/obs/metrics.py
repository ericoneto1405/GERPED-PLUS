"""
Sistema de Métricas Prometheus
================================

Coleta e exporta métricas da aplicação para monitoramento com Prometheus/Grafana.

Métricas Coletadas:
- http_requests_total: Total de requisições HTTP
- http_request_duration_seconds: Duração das requisições
- http_requests_in_progress: Requisições em andamento
- business_operations_total: Operações de negócio (pedidos, pagamentos, etc)
- database_queries_total: Total de queries executadas
- cache_operations_total: Operações de cache (hit/miss)

Endpoint:
    GET /metrics - Exporta métricas no formato Prometheus

Uso:
    from meu_app.obs.metrics import track_request, business_operation
    
    @track_request
    def minha_rota():
        ...
    
    business_operation('pedido', 'criacao')

Autor: Sistema GERPED
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from flask import request
import time
import functools
from typing import Callable


# ===========================
# MÉTRICAS HTTP
# ===========================

http_requests_total = Counter(
    'http_requests_total',
    'Total de requisições HTTP',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'Duração das requisições HTTP em segundos',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Requisições HTTP em andamento',
    ['method', 'endpoint']
)

# ===========================
# MÉTRICAS DE NEGÓCIO
# ===========================

business_operations_total = Counter(
    'business_operations_total',
    'Total de operações de negócio',
    ['module', 'operation', 'status']
)

business_operation_duration_seconds = Histogram(
    'business_operation_duration_seconds',
    'Duração de operações de negócio',
    ['module', 'operation'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

# ===========================
# MÉTRICAS DE BANCO DE DADOS
# ===========================

database_queries_total = Counter(
    'database_queries_total',
    'Total de queries de banco de dados',
    ['operation', 'table']
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Duração de queries de banco de dados',
    ['operation'],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0)
)

# ===========================
# MÉTRICAS DE CACHE
# ===========================

cache_operations_total = Counter(
    'cache_operations_total',
    'Total de operações de cache',
    ['operation', 'result']  # operation: get/set/delete, result: hit/miss/success
)

# ===========================
# MÉTRICAS DE APLICAÇÃO
# ===========================

app_info = Gauge(
    'app_info',
    'Informações da aplicação',
    ['version', 'environment']
)


def init_metrics(app):
    """
    Inicializa o sistema de métricas.
    
    Args:
        app: Instância Flask
    """
    # Configurar informações da aplicação
    version = app.config.get('VERSION', '1.0.0')
    environment = app.config.get('ENV', 'development')
    
    app_info.labels(version=version, environment=environment).set(1)
    
    app.logger.info(
        'Sistema de métricas Prometheus inicializado',
        extra={
            'version': version,
            'environment': environment
        }
    )


def track_request(f: Callable) -> Callable:
    """
    Decorator para rastrear métricas de requisições HTTP.
    
    Registra:
    - Total de requisições
    - Duração da requisição
    - Requisições em andamento
    
    Uso:
        @app.route('/api/pedidos')
        @track_request
        def listar_pedidos():
            ...
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        method = request.method
        endpoint = request.endpoint or 'unknown'
        
        # Incrementar requisições em andamento
        http_requests_in_progress.labels(
            method=method,
            endpoint=endpoint
        ).inc()
        
        start_time = time.time()
        status = 500  # Default para erros não capturados
        
        try:
            response = f(*args, **kwargs)
            
            # Extrair status code
            if isinstance(response, tuple):
                status = response[1] if len(response) > 1 else 200
            else:
                status = getattr(response, 'status_code', 200)
            
            return response
            
        except Exception as e:
            status = 500
            raise
            
        finally:
            # Calcular duração
            duration = time.time() - start_time
            
            # Decrementar requisições em andamento
            http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).dec()
            
            # Registrar métricas
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
    
    return wrapper


def business_operation(module: str, operation: str, status: str = 'success'):
    """
    Registra uma operação de negócio.
    
    Args:
        module: Módulo (pedidos, pagamentos, etc)
        operation: Operação (criacao, atualizacao, exclusao)
        status: Status (success, error, validation_error)
        
    Exemplo:
        >>> business_operation('pedidos', 'criacao', 'success')
        >>> business_operation('pagamentos', 'aprovacao', 'error')
    """
    business_operations_total.labels(
        module=module,
        operation=operation,
        status=status
    ).inc()


def track_business_operation(module: str, operation: str):
    """
    Decorator para rastrear operações de negócio.
    
    Args:
        module: Módulo (pedidos, clientes, etc)
        operation: Operação (criar, atualizar, deletar)
        
    Uso:
        @track_business_operation('pedidos', 'criacao')
        def criar_pedido(dados):
            ...
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            
            try:
                result = f(*args, **kwargs)
                
                # Detectar se operação falhou
                if isinstance(result, tuple):
                    sucesso = result[0] if len(result) > 0 else False
                    if not sucesso:
                        status = 'error'
                
                return result
                
            except Exception as e:
                status = 'error'
                raise
                
            finally:
                # Registrar métricas
                duration = time.time() - start_time
                
                business_operations_total.labels(
                    module=module,
                    operation=operation,
                    status=status
                ).inc()
                
                business_operation_duration_seconds.labels(
                    module=module,
                    operation=operation
                ).observe(duration)
        
        return wrapper
    return decorator


def track_db_query(operation: str, table: str = 'unknown'):
    """
    Registra uma query de banco de dados.
    
    Args:
        operation: Tipo de operação (SELECT, INSERT, UPDATE, DELETE)
        table: Nome da tabela
        
    Exemplo:
        >>> track_db_query('SELECT', 'pedidos')
        >>> track_db_query('INSERT', 'clientes')
    """
    database_queries_total.labels(
        operation=operation,
        table=table
    ).inc()


def track_cache_operation(operation: str, result: str):
    """
    Registra uma operação de cache.
    
    Args:
        operation: Operação (get, set, delete)
        result: Resultado (hit, miss, success, error)
        
    Exemplo:
        >>> track_cache_operation('get', 'hit')
        >>> track_cache_operation('get', 'miss')
        >>> track_cache_operation('set', 'success')
    """
    cache_operations_total.labels(
        operation=operation,
        result=result
    ).inc()


def export_metrics():
    """
    Exporta métricas no formato Prometheus.
    
    Returns:
        Métricas formatadas para Prometheus
        
    Uso (Flask route):
        @app.route('/metrics')
        def metrics():
            return export_metrics(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    """
    return generate_latest(REGISTRY)

