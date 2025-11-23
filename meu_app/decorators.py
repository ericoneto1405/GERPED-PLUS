"""
Decoradores de Acesso e Segurança
================================

Este módulo contém decoradores centralizados para controle de acesso,
autenticação e validação de permissões no sistema.

Autor: Sistema de Gestão Empresarial
Data: 2024
"""

from functools import wraps
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone

from flask import current_app, jsonify, redirect, request, session, url_for
from flask_login import current_user


def _register_rollout_event(event_type: str, descricao: str, extras: Optional[Dict[str, Any]] = None):
    """
    Registra evento relacionado ao rollout usando o módulo de log de atividades.
    Importação lazy para evitar dependência circular durante import.
    """
    try:
        from .log_atividades.services import LogAtividadesService  # noqa: WPS433 import inside function
        service = LogAtividadesService()
        service.registrar_atividade(
            tipo_atividade=event_type,
            titulo="Controle de Go-Live",
            descricao=descricao,
            modulo='rollout',
            dados_extras=extras or {},
            ip_address=request.remote_addr
        )
    except Exception as exc:  # pragma: no cover - logging defensivo
        current_app.logger.error(f"Falha ao registrar evento de rollout: {exc}")


def _rollout_allows_access() -> Tuple[bool, Optional[Tuple[Any, int, Dict[str, str]]]]:
    """
    Controla o acesso enquanto o go-live estiver restrito a um grupo interno.
    Retorna (permitido, (response_body, status_code, headers_dict)).
    """
    rollout_cfg = current_app.config.get('ROLLOUT_CONTROL') or {}
    if not rollout_cfg.get('enabled'):
        return True, None

    start_at = rollout_cfg.get('start_at')
    internal_days = rollout_cfg.get('internal_days', 7)

    # Se não houver data configurada, utiliza o primeiro acesso como marco inicial.
    if start_at is None:
        start_at = datetime.now(timezone.utc)
        rollout_cfg['start_at'] = start_at
        _register_rollout_event(
            'rollout_iniciado',
            f"Rollout interno iniciado automaticamente em {start_at.isoformat()}",
        )

    # Desativa controle após janela interna expirar
    if internal_days is not None and internal_days >= 0:
        janela_final = start_at + timedelta(days=internal_days)
        if datetime.now(timezone.utc) >= janela_final:
            rollout_cfg['enabled'] = False
            current_app.logger.info("Janela de rollout interno expirou; acesso público liberado automaticamente.")
            _register_rollout_event(
                'rollout_concluido',
                'Janela de go-live interno concluída automaticamente; acesso liberado.',
                {'start_at': start_at.isoformat(), 'internal_days': internal_days}
            )
            return True, None

    usuario_nome = (session.get('usuario_nome') or '').lower()
    usuario_tipo = (session.get('usuario_tipo') or '').lower()

    allowed_roles = {role.lower() for role in rollout_cfg.get('allowed_roles', [])}
    allowed_users = {user.lower() for user in rollout_cfg.get('allowed_users', [])}

    if usuario_tipo in allowed_roles or usuario_nome in allowed_users:
        return True, None

    mensagem = rollout_cfg.get(
        'blocked_message',
        'Ambiente em go-live controlado. Tente novamente após a liberação oficial.'
    )

    current_app.logger.warning(
        "Acesso bloqueado durante rollout: usuário=%s, role=%s, rota=%s",
        session.get('usuario_nome', 'desconhecido'),
        session.get('usuario_tipo', 'desconhecido'),
        request.path,
    )
    _register_rollout_event(
        'rollout_acesso_negado',
        f"Acesso negado a {session.get('usuario_nome', 'desconhecido')} na rota {request.path}",
        {
            'usuario': session.get('usuario_nome'),
            'tipo': session.get('usuario_tipo'),
            'endpoint': request.endpoint,
            'path': request.path,
        }
    )

    payload = {
        'error': True,
        'message': mensagem,
        'type': 'RolloutRestrictedAccess',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }

    body = jsonify(payload)
    return False, (body, 403, {'Retry-After': '3600'})


def login_obrigatorio(f):
    """
    Decorador que verifica se o usuário está logado
    
    Args:
        f: Função a ser decorada
        
    Returns:
        Função decorada que verifica autenticação
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        is_authenticated = getattr(current_user, 'is_authenticated', False)
        if not is_authenticated or 'usuario_id' not in session:
            # Se for uma requisição AJAX ou API, retornar JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.path.startswith('/api/') or \
               request.headers.get('Accept') == 'application/json':
                return jsonify({
                    'error': True,
                    'message': 'Acesso negado. Faça login para continuar.',
                    'type': 'AuthenticationRequired',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }), 401
            
            # Para requisições normais, redirecionar para login
            return redirect(url_for('main.login'))
        
        permitido, resposta = _rollout_allows_access()
        if not permitido and resposta:
            body, status, headers = resposta
            return body, status, headers
        
        return f(*args, **kwargs)
    return decorated_function


def permissao_necessaria(permissao):
    """
    Decorador que verifica se o usuário tem a permissão necessária
    
    Args:
        permissao (str): Nome da permissão necessária (ex: 'acesso_clientes')
        
    Returns:
        Decorador que verifica permissão
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Primeiro verificar se está logado
            is_authenticated = getattr(current_user, 'is_authenticated', False)
            if not is_authenticated or 'usuario_id' not in session:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                   request.path.startswith('/api/') or \
                   request.headers.get('Accept') == 'application/json':
                    return jsonify({
                        'error': True,
                        'message': 'Acesso negado. Faça login para continuar.',
                        'type': 'AuthenticationRequired',
                        'timestamp': datetime.now().isoformat()
                    }), 401
                return redirect(url_for('main.login'))
            
            # Verificar se tem a permissão necessária
            # Admin tem acesso a todas as permissões
            if session.get('usuario_tipo') == 'admin':
                return f(*args, **kwargs)

            if not session.get(permissao, False):
                current_app.logger.warning(
                    f"Tentativa de acesso negada: usuário {session.get('usuario_nome', 'desconhecido')} "
                    f"tentou acessar {request.endpoint} sem permissão '{permissao}' "
                    f"(IP: {request.remote_addr})"
                )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                   request.path.startswith('/api/') or \
                   request.headers.get('Accept') == 'application/json':
                    return jsonify({
                        'error': True,
                        'message': f'Acesso negado. Você não tem permissão para acessar esta funcionalidade.',
                        'type': 'InsufficientPermissions',
                        'permission_required': permissao,
                        'timestamp': datetime.now().isoformat()
                    }), 403
                
                return jsonify({
                    'error': True,
                    'message': f'Acesso negado. Você não tem permissão para acessar esta funcionalidade.',
                    'type': 'InsufficientPermissions',
                    'permission_required': permissao,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_necessario(f):
    """
    Decorador que verifica se o usuário é administrador
    
    Args:
        f: Função a ser decorada
        
    Returns:
        Função decorada que verifica se é admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Primeiro verificar se está logado
        if 'usuario_id' not in session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.path.startswith('/api/') or \
               request.headers.get('Accept') == 'application/json':
                return jsonify({
                    'error': True,
                    'message': 'Acesso negado. Faça login para continuar.',
                    'type': 'AuthenticationRequired',
                    'timestamp': datetime.now().isoformat()
                }), 401
            return redirect(url_for('main.login'))
        
        # Verificar se é administrador
        if session.get('usuario_tipo') != 'admin':
            current_app.logger.warning(
                f"Tentativa de acesso de não-admin: usuário {session.get('usuario_nome', 'desconhecido')} "
                f"tentou acessar {request.endpoint} (IP: {request.remote_addr})"
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.path.startswith('/api/') or \
               request.headers.get('Accept') == 'application/json':
                return jsonify({
                    'error': True,
                    'message': 'Acesso negado. Apenas administradores podem acessar esta funcionalidade.',
                    'type': 'AdminRequired',
                    'timestamp': datetime.now().isoformat()
                }), 403
            
            return jsonify({
                'error': True,
                'message': 'Acesso negado. Apenas administradores podem acessar esta funcionalidade.',
                'type': 'AdminRequired',
                'timestamp': datetime.now().isoformat()
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


def validar_metodo_http(metodos_permitidos):
    """
    Decorador que valida o método HTTP da requisição
    
    Args:
        metodos_permitidos (list): Lista de métodos HTTP permitidos
        
    Returns:
        Decorador que valida método HTTP
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.method not in metodos_permitidos:
                current_app.logger.warning(
                    f"Método HTTP não permitido: {request.method} para {request.endpoint} "
                    f"(IP: {request.remote_addr})"
                )
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                   request.path.startswith('/api/') or \
                   request.headers.get('Accept') == 'application/json':
                    return jsonify({
                        'error': True,
                        'message': f'Método {request.method} não permitido para esta rota.',
                        'type': 'MethodNotAllowed',
                        'allowed_methods': metodos_permitidos,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }), 405
                
                return jsonify({
                    'error': True,
                    'message': f'Método {request.method} não permitido para esta rota.',
                    'type': 'MethodNotAllowed',
                    'allowed_methods': metodos_permitidos,
                    'timestamp': datetime.now().isoformat()
                }), 405
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_acesso(modulo):
    """
    Decorador que registra o acesso a funcionalidades sensíveis
    
    Args:
        modulo (str): Nome do módulo acessado
        
    Returns:
        Decorador que registra acesso
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Registrar acesso
            current_app.logger.info(
                f"Acesso autorizado: usuário {session.get('usuario_nome', 'desconhecido')} "
                f"acessou {request.endpoint} no módulo {modulo} "
                f"(IP: {request.remote_addr})"
            )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Decoradores compostos para facilitar o uso
def login_e_permissao(permissao):
    """
    Decorador composto que verifica login e permissão
    
    Args:
        permissao (str): Nome da permissão necessária
        
    Returns:
        Decorador composto
    """
    def decorator(f):
        @wraps(f)
        @login_obrigatorio
        @permissao_necessaria(permissao)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def login_e_admin():
    """
    Decorador composto que verifica login e se é admin
    
    Returns:
        Decorador composto
    """
    def decorator(f):
        @wraps(f)
        @login_obrigatorio
        @admin_necessario
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator
