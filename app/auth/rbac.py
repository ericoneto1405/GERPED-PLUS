"""
Sistema de Autorização por Papéis (RBAC)
=========================================

Implementa controle de acesso baseado em roles/papéis com logging estruturado.

Papéis definidos:
- ADMIN: Acesso total (gestão de usuários, configurações)
- FINANCEIRO: Módulos financeiro e apuração
- LOGISTICA: Módulos de coletas e recibos
- VENDEDOR: Painel do vendedor
- COMUM: Acesso básico (clientes, produtos, pedidos)

Autor: Sistema GERPED
Data: Outubro 2025
"""

from functools import wraps
from typing import List, Set

from flask import abort, current_app, jsonify, render_template, request, session


# Definição de papéis e mapeamento para permissões
ROLE_PERMISSIONS_MAP = {
    'ADMIN': {
        'acesso_clientes', 'acesso_produtos', 'acesso_pedidos',
        'acesso_financeiro', 'acesso_logistica', 'admin'
    },
    'FINANCEIRO': {
        'acesso_clientes', 'acesso_produtos', 'acesso_pedidos',
        'acesso_financeiro'
    },
    'LOGISTICA': {
        'acesso_clientes', 'acesso_produtos', 'acesso_pedidos',
        'acesso_logistica'
    },
    'VENDEDOR': {
        'acesso_clientes', 'acesso_produtos', 'acesso_pedidos'
    },
    'COMUM': {
        'acesso_clientes', 'acesso_produtos'
    }
}


def get_user_roles() -> Set[str]:
    """
    Determina os papéis do usuário logado baseado em suas permissões.
    
    Returns:
        Set[str]: Conjunto de papéis do usuário
    """
    if 'usuario_id' not in session:
        return set()
    
    roles = set()
    
    # Verificar se é admin
    if session.get('usuario_tipo') == 'admin':
        roles.add('ADMIN')
        return roles  # Admin tem acesso total
    
    # Mapear permissões para roles
    user_permissions = set()
    if session.get('acesso_clientes'):
        user_permissions.add('acesso_clientes')
    if session.get('acesso_produtos'):
        user_permissions.add('acesso_produtos')
    if session.get('acesso_pedidos'):
        user_permissions.add('acesso_pedidos')
    if session.get('acesso_financeiro'):
        user_permissions.add('acesso_financeiro')
    if session.get('acesso_logistica'):
        user_permissions.add('acesso_logistica')
    
    # Determinar roles baseado em permissões
    for role, permissions in ROLE_PERMISSIONS_MAP.items():
        if role == 'ADMIN':
            continue  # Já verificado acima
        if permissions.issubset(user_permissions):
            roles.add(role)
    
    # Se tem pelo menos permissões básicas, adicionar COMUM
    if user_permissions:
        roles.add('COMUM')
    
    return roles


def has_any_role(required_roles: List[str]) -> bool:
    """
    Verifica se o usuário tem pelo menos um dos papéis requeridos.
    
    Args:
        required_roles: Lista de papéis aceitos
        
    Returns:
        bool: True se usuário tem pelo menos um papel
    """
    user_roles = get_user_roles()
    return bool(user_roles.intersection(required_roles))


def requires_roles(*roles):
    """
    Decorator que verifica se o usuário tem pelo menos um dos papéis especificados.
    
    Funcionalidades:
    - Verifica autenticação (login)
    - Verifica autorização (papel/role)
    - Logging estruturado de negações
    - Retorna 403 com template amigável ou JSON
    
    Args:
        *roles: Papéis aceitos (ex: 'ADMIN', 'FINANCEIRO', 'LOGISTICA')
        
    Returns:
        Decorator que verifica autorização
        
    Exemplo:
        @requires_roles('ADMIN', 'FINANCEIRO')
        def lancar_pagamento():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Verificar se está logado
            if 'usuario_id' not in session:
                current_app.logger.warning(
                    f"[RBAC] Acesso negado (não autenticado): "
                    f"endpoint={request.endpoint}, ip={request.remote_addr}"
                )
                
                if _wants_json_response():
                    return jsonify({
                        'error': True,
                        'message': 'Autenticação necessária. Faça login para continuar.',
                        'type': 'AuthenticationRequired',
                        'required_roles': list(roles)
                    }), 401
                
                from flask import redirect, url_for
                return redirect(url_for('main.login'))
            
            # 2. Verificar se tem o papel necessário
            if not has_any_role(list(roles)):
                user_roles = get_user_roles()
                
                # Logging estruturado de negação de acesso
                current_app.logger.warning(
                    f"[RBAC] Acesso negado (autorização insuficiente): "
                    f"user_id={session.get('usuario_id')}, "
                    f"username={session.get('usuario_nome')}, "
                    f"user_roles={list(user_roles)}, "
                    f"required_roles={list(roles)}, "
                    f"endpoint={request.endpoint}, "
                    f"method={request.method}, "
                    f"ip={request.remote_addr}, "
                    f"path={request.path}"
                )
                
                if _wants_json_response():
                    return jsonify({
                        'error': True,
                        'message': 'Acesso negado. Você não tem permissão para esta funcionalidade.',
                        'type': 'InsufficientPermissions',
                        'required_roles': list(roles),
                        'user_roles': list(user_roles)
                    }), 403
                
                # Retornar template 403 amigável
                abort(403)
            
            # 3. Logging de acesso autorizado
            current_app.logger.info(
                f"[RBAC] Acesso autorizado: "
                f"user_id={session.get('usuario_id')}, "
                f"username={session.get('usuario_nome')}, "
                f"roles={list(get_user_roles())}, "
                f"endpoint={request.endpoint}"
            )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _wants_json_response() -> bool:
    """Detecta se a requisição espera JSON."""
    if request.is_json:
        return True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    if request.path.startswith('/api/'):
        return True
    accepts = request.accept_mimetypes
    return accepts.best == 'application/json'


# Aliases para facilitar uso
requires_admin = lambda f: requires_roles('ADMIN')(f)
requires_financeiro = lambda f: requires_roles('ADMIN', 'FINANCEIRO')(f)
requires_logistica = lambda f: requires_roles('ADMIN', 'LOGISTICA')(f)
requires_vendedor = lambda f: requires_roles('ADMIN', 'VENDEDOR', 'FINANCEIRO')(f)


__all__ = [
    'requires_roles',
    'requires_admin',
    'requires_financeiro',
    'requires_logistica',
    'requires_vendedor',
    'get_user_roles',
    'has_any_role',
    'ROLE_PERMISSIONS_MAP'
]
