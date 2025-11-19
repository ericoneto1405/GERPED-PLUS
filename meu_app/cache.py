"""
Sistema de Cache Inteligente com Invalidação por Evento
========================================================

Sistema de cache com Redis que oferece:
- Cache por chave configurável
- TTL por rota
- Invalidação automática por evento
- Suporte a múltiplas estratégias de invalidação
- Tracking de cache hit/miss via métricas

Uso:
    # Cache simples
    @cached(timeout=300, key_prefix='dashboard')
    def dashboard():
        return render_template('dashboard.html')
    
    # Cache com invalidação por evento
    @cached_with_invalidation(
        timeout=600,
        key_prefix='vendedor_apuracao',
        invalidate_on=['pedido.criado', 'pagamento.aprovado']
    )
    def apuracao_vendedor(vendedor_id):
        return calcular_apuracao(vendedor_id)
    
    # Invalidar cache manualmente
    invalidate_cache(['pedido.criado'])

Autor: Sistema GERPED - Fase 8
Data: Outubro 2025
"""

import functools
import hashlib
from typing import Callable, List, Optional, Any, Union
from flask import request, current_app
from werkzeug.exceptions import BadRequest

# Importar cache da instância
from . import flask_cache as cache_instance

# Importar métricas para tracking
try:
    from .obs.metrics import track_cache_operation
except ImportError:
    # Fallback se métricas não estiverem disponíveis
    def track_cache_operation(operation: str, result: str):
        pass


# ===========================
# CONFIGURAÇÃO DE EVENTOS
# ===========================

# Mapeamento de eventos para padrões de chave de cache
CACHE_INVALIDATION_MAP = {
    # Pedidos
    'pedido.criado': [
        'dashboard_*',
        'vendedor_apuracao_*',
        'vendedor_pedidos_*',
        'apuracao_mes_*'
    ],
    'pedido.atualizado': [
        'dashboard_*',
        'vendedor_apuracao_*',
        'vendedor_pedidos_*',
        'pedido_detalhe_*'
    ],
    'pedido.cancelado': [
        'dashboard_*',
        'vendedor_apuracao_*',
        'vendedor_pedidos_*'
    ],
    
    # Pagamentos
    'pagamento.aprovado': [
        'dashboard_*',
        'vendedor_apuracao_*',
        'financeiro_dashboard_*',
        'apuracao_mes_*'
    ],
    'pagamento.rejeitado': [
        'financeiro_dashboard_*'
    ],
    
    # Coletas
    'coleta.concluida': [
        'dashboard_*',
        'vendedor_apuracao_*',
        'logistica_dashboard_*'
    ],
    
    # Apuração
    'apuracao.criada': [
        'dashboard_*',
        'apuracao_mes_*',
        'apuracao_lista_*'
    ],
    'apuracao.atualizada': [
        'apuracao_mes_*',
        'apuracao_detalhe_*'
    ],
    
    # Produtos
    'produto.atualizado': [
        'produto_lista_*',
        'produto_detalhe_*'
    ],
    
    # Clientes
    'cliente.atualizado': [
        'cliente_lista_*',
        'cliente_detalhe_*'
    ]
}


# ===========================
# FUNÇÕES DE CACHE
# ===========================

def make_cache_key(*args, **kwargs) -> str:
    """
    Gera uma chave de cache baseada nos argumentos.
    
    Args:
        *args: Argumentos posicionais
        **kwargs: Argumentos nomeados
        
    Returns:
        Chave de cache única
    """
    # Incluir query params se houver request
    cache_key_parts = []
    
    if args:
        cache_key_parts.extend([str(arg) for arg in args])
    
    if kwargs:
        cache_key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    
    # Adicionar query params do request se disponível
    try:
        if request and request.args:
            query_string = '&'.join(
                f"{k}={v}" for k, v in sorted(request.args.items())
            )
            if query_string:
                cache_key_parts.append(query_string)
    except RuntimeError:
        pass  # Fora de contexto de request
    
    # Gerar hash MD5 para chave compacta
    key_string = ':'.join(cache_key_parts)
    if key_string:
        return hashlib.md5(key_string.encode()).hexdigest()
    return 'default'


def cached(
    timeout: int = 300,
    key_prefix: Optional[str] = None,
    unless: Optional[Callable] = None,
    make_cache_key_fn: Optional[Callable] = None
) -> Callable:
    """
    Decorator de cache simples para endpoints.
    
    Args:
        timeout: Tempo de expiração em segundos (default: 300s = 5min)
        key_prefix: Prefixo da chave de cache
        unless: Função que retorna True para pular cache
        make_cache_key_fn: Função customizada para gerar chave
        
    Returns:
        Decorator de cache
        
    Exemplo:
        @cached(timeout=600, key_prefix='dashboard')
        def dashboard():
            return render_template('dashboard.html')
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            # Verificar se deve pular cache
            if unless and unless():
                return f(*args, **kwargs)
            
            # Gerar chave de cache
            if make_cache_key_fn:
                cache_key_suffix = make_cache_key_fn(*args, **kwargs)
            else:
                cache_key_suffix = make_cache_key(*args, **kwargs)
            
            cache_key = f"{key_prefix}_{cache_key_suffix}" if key_prefix else cache_key_suffix
            
            # Tentar obter do cache
            try:
                cached_value = cache_instance.get(cache_key)
                if cached_value is not None:
                    track_cache_operation('get', 'hit')
                    current_app.logger.debug(
                        f"Cache HIT: {cache_key}",
                        extra={'cache_key': cache_key}
                    )
                    return cached_value
                
                track_cache_operation('get', 'miss')
                current_app.logger.debug(
                    f"Cache MISS: {cache_key}",
                    extra={'cache_key': cache_key}
                )
            except Exception as e:
                current_app.logger.warning(
                    f"Erro ao buscar cache: {str(e)}",
                    extra={'cache_key': cache_key}
                )
            
            # Executar função e cachear resultado
            result = f(*args, **kwargs)
            
            try:
                cache_instance.set(cache_key, result, timeout=timeout)
                track_cache_operation('set', 'success')
                current_app.logger.debug(
                    f"Cache SET: {cache_key} (TTL: {timeout}s)",
                    extra={'cache_key': cache_key, 'ttl': timeout}
                )
            except Exception as e:
                current_app.logger.error(
                    f"Erro ao salvar cache: {str(e)}",
                    extra={'cache_key': cache_key}
                )
                track_cache_operation('set', 'error')
            
            return result
        
        return wrapper
    return decorator


def cached_with_invalidation(
    timeout: int = 300,
    key_prefix: Optional[str] = None,
    invalidate_on: Optional[List[str]] = None
) -> Callable:
    """
    Decorator de cache com invalidação automática por eventos.
    
    Args:
        timeout: Tempo de expiração em segundos
        key_prefix: Prefixo da chave de cache
        invalidate_on: Lista de eventos que invalidam este cache
        
    Returns:
        Decorator de cache com invalidação
        
    Exemplo:
        @cached_with_invalidation(
            timeout=600,
            key_prefix='vendedor_apuracao',
            invalidate_on=['pedido.criado', 'pagamento.aprovado']
        )
        def apuracao_vendedor(vendedor_id):
            return calcular_apuracao(vendedor_id)
    """
    # Registrar mapping de invalidação
    if invalidate_on and key_prefix:
        for event in invalidate_on:
            if event not in CACHE_INVALIDATION_MAP:
                CACHE_INVALIDATION_MAP[event] = []
            
            pattern = f"{key_prefix}_*"
            if pattern not in CACHE_INVALIDATION_MAP[event]:
                CACHE_INVALIDATION_MAP[event].append(pattern)
    
    # Usar decorator de cache padrão
    return cached(timeout=timeout, key_prefix=key_prefix)


def invalidate_cache(
    events: Union[str, List[str]],
    specific_keys: Optional[List[str]] = None
) -> int:
    """
    Invalida cache baseado em eventos ou chaves específicas.
    
    Args:
        events: Evento ou lista de eventos que ocorreram
        specific_keys: Chaves específicas para invalidar (opcional)
        
    Returns:
        Número de chaves invalidadas
        
    Exemplo:
        # Invalidar por evento
        invalidate_cache('pedido.criado')
        
        # Invalidar múltiplos eventos
        invalidate_cache(['pedido.criado', 'pagamento.aprovado'])
        
        # Invalidar chaves específicas
        invalidate_cache('pedido.atualizado', specific_keys=['pedido_detalhe_123'])
    """
    if isinstance(events, str):
        events = [events]
    
    keys_to_invalidate = set()
    
    # Adicionar chaves específicas
    if specific_keys:
        keys_to_invalidate.update(specific_keys)
    
    # Adicionar chaves baseadas em eventos
    for event in events:
        if event in CACHE_INVALIDATION_MAP:
            patterns = CACHE_INVALIDATION_MAP[event]
            for pattern in patterns:
                # Buscar chaves que correspondem ao padrão
                try:
                    # Redis pattern matching
                    matching_keys = cache_instance.cache._read_client.keys(
                        f"flask_cache_{pattern}"
                    )
                    keys_to_invalidate.update(
                        [key.decode() if isinstance(key, bytes) else key 
                         for key in matching_keys]
                    )
                except Exception as e:
                    current_app.logger.warning(
                        f"Erro ao buscar chaves para padrão {pattern}: {str(e)}"
                    )
    
    # Invalidar chaves
    count = 0
    for key in keys_to_invalidate:
        try:
            # Remover prefixo flask_cache_ se presente
            cache_key = key.replace('flask_cache_', '')
            if cache_instance.delete(cache_key):
                count += 1
        except Exception as e:
            current_app.logger.error(
                f"Erro ao invalidar chave {key}: {str(e)}"
            )
    
    if count > 0:
        current_app.logger.info(
            f"Cache invalidado: {count} chaves",
            extra={
                'events': events,
                'keys_invalidated': count
            }
        )
        track_cache_operation('delete', 'success')
    
    return count


def clear_all_cache() -> bool:
    """
    Limpa todo o cache da aplicação.
    
    ⚠️ Use com cuidado! Isso afetará a performance temporariamente.
    
    Returns:
        True se sucesso
        
    Exemplo:
        clear_all_cache()
    """
    try:
        cache_instance.clear()
        current_app.logger.warning("TODO o cache foi limpo!")
        return True
    except Exception as e:
        current_app.logger.error(f"Erro ao limpar cache: {str(e)}")
        return False


# ===========================
# HELPERS PARA DECORATORS
# ===========================

def unless_authenticated() -> bool:
    """
    Helper para pular cache se usuário estiver autenticado.
    
    Uso:
        @cached(timeout=300, unless=unless_authenticated)
    """
    from flask_login import current_user
    return current_user.is_authenticated


def unless_post_request() -> bool:
    """
    Helper para pular cache em requisições POST.
    
    Uso:
        @cached(timeout=300, unless=unless_post_request)
    """
    return request.method == 'POST'


# ===========================
# CONFIGURAÇÃO DE CACHE
# ===========================

def configure_cache_for_production(app):
    """
    Configuração de cache otimizada para produção.
    
    Args:
        app: Instância Flask
    """
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    
    app.config.update({
        'CACHE_TYPE': 'redis',
        'CACHE_REDIS_URL': redis_url,
        'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutos
        'CACHE_KEY_PREFIX': 'flask_cache_',
        
        # Opções Redis
        'CACHE_OPTIONS': {
            'socket_connect_timeout': 2,
            'socket_timeout': 2,
            'connection_pool_kwargs': {
                'max_connections': 50
            }
        }
    })
    
    app.logger.info(
        'Cache Redis configurado para produção',
        extra={'redis_url': redis_url}
    )


def get_cache_stats() -> dict:
    """
    Retorna estatísticas do cache.
    
    Returns:
        Dicionário com estatísticas
        
    Exemplo:
        stats = get_cache_stats()
        print(f"Eventos mapeados: {stats['events_count']}")
    """
    try:
        # Contar chaves no cache
        keys_count = len(cache_instance.cache._read_client.keys('flask_cache_*'))
    except Exception:
        keys_count = 0
    
    return {
        'events_count': len(CACHE_INVALIDATION_MAP),
        'keys_count': keys_count,
        'invalidation_patterns': sum(
            len(patterns) for patterns in CACHE_INVALIDATION_MAP.values()
        )
    }

