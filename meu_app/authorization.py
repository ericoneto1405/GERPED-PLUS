"""
Módulo de Autorização e Prevenção de IDOR
==========================================

Implementa:
- Object-level authorization (previne IDOR)
- Verificação de ownership de recursos
- Mass assignment protection
"""
from functools import wraps
from flask import abort, session, current_app, request, jsonify
from typing import Optional, Callable


def owns_resource(resource_type: str, id_param: str = 'id', check_function: Optional[Callable] = None):
    """
    Decorador para verificar se usuário tem acesso ao recurso (anti-IDOR)
    
    Args:
        resource_type: Tipo do recurso ('pedido', 'cliente', 'coleta', etc)
        id_param: Nome do parâmetro que contém o ID do recurso
        check_function: Função customizada de verificação (opcional)
    
    Exemplo:
        @owns_resource('pedido', 'pedido_id')
        def editar_pedido(pedido_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Obter ID do recurso
            resource_id = kwargs.get(id_param) or request.view_args.get(id_param)
            
            if not resource_id:
                current_app.logger.error(f"ID do recurso não encontrado: {id_param}")
                abort(400, "ID do recurso inválido")
            
            # Obter dados do usuário
            user_id = session.get('usuario_id')
            user_type = session.get('usuario_tipo')
            
            if not user_id:
                abort(401, "Não autenticado")
            
            # Admin tem acesso a tudo
            if user_type == 'admin':
                return f(*args, **kwargs)
            
            # Usar função customizada se fornecida
            if check_function:
                if not check_function(user_id, resource_id):
                    current_app.logger.warning(
                        f"[IDOR] Tentativa de acesso não autorizado: "
                        f"user={user_id}, resource={resource_type}:{resource_id}, "
                        f"ip={request.remote_addr}"
                    )
                    abort(403, "Acesso negado a este recurso")
                return f(*args, **kwargs)
            
            # Verificação padrão por tipo de recurso
            has_access = _check_default_ownership(
                user_id, resource_type, resource_id
            )
            
            if not has_access:
                current_app.logger.warning(
                    f"[IDOR] Tentativa de acesso não autorizado: "
                    f"user={user_id}, resource={resource_type}:{resource_id}, "
                    f"ip={request.remote_addr}"
                )
                abort(403, "Acesso negado a este recurso")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _check_default_ownership(user_id: int, resource_type: str, resource_id: int) -> bool:
    """
    Verificação padrão de ownership por tipo de recurso
    
    Returns:
        True se usuário tem acesso, False caso contrário
    """
    from meu_app import db
    
    try:
        if resource_type == 'pedido':
            from meu_app.models import Pedido
            pedido = db.session.get(Pedido, resource_id)
            # Verificar se pedido pertence ao cliente do usuário (se vendedor)
            # Ou permitir se tem permissão de pedidos
            return pedido is not None and session.get('acesso_pedidos', False)
        
        elif resource_type == 'cliente':
            from meu_app.models import Cliente
            cliente = db.session.get(Cliente, resource_id)
            return cliente is not None and session.get('acesso_clientes', False)
        
        elif resource_type == 'coleta':
            from meu_app.models import Coleta
            coleta = db.session.get(Coleta, resource_id)
            return coleta is not None and session.get('acesso_logistica', False)
        
        elif resource_type == 'usuario':
            # Apenas admin ou próprio usuário pode acessar
            return user_id == resource_id
        
        else:
            # Tipo desconhecido - negar por padrão
            current_app.logger.warning(f"Tipo de recurso desconhecido: {resource_type}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"Erro em _check_default_ownership: {e}")
        return False


class FieldWhitelist:
    """
    Proteção contra mass assignment
    
    Define campos permitidos para cada operação
    """
    
    # Campos permitidos por entidade (evita mass assignment)
    ALLOWED_FIELDS = {
        'usuario': {
            'create': ['nome', 'senha', 'tipo', 'acesso_clientes', 'acesso_produtos', 
                      'acesso_pedidos', 'acesso_financeiro', 'acesso_logistica'],
            'update': ['nome', 'acesso_clientes', 'acesso_produtos', 
                      'acesso_pedidos', 'acesso_financeiro', 'acesso_logistica'],
            'update_self': ['nome'],  # Usuário editando próprio perfil
        },
        'cliente': {
            'create': ['nome', 'fantasia', 'cpf_cnpj', 'endereco', 'cidade', 
                      'telefone', 'email'],
            'update': ['nome', 'fantasia', 'endereco', 'cidade', 'telefone', 'email'],
        },
        'produto': {
            'create': ['nome', 'categoria', 'codigo_interno', 'ean', 'preco_medio'],
            'update': ['nome', 'categoria', 'preco_medio'],
        },
        'pedido': {
            'create': ['cliente_id', 'data', 'vendedor_id'],
            'update': ['data'],  # Status não pode ser alterado diretamente
        },
    }
    
    @classmethod
    def filter_fields(cls, entity: str, operation: str, data: dict, user_role: str = None) -> dict:
        """
        Filtra dados removendo campos não permitidos
        
        Args:
            entity: Tipo de entidade ('usuario', 'cliente', etc)
            operation: Operação ('create', 'update', 'update_self')
            data: Dicionário com dados a filtrar
            user_role: Role do usuário (para lógica condicional)
            
        Returns:
            Dicionário filtrado apenas com campos permitidos
        """
        entity_config = cls.ALLOWED_FIELDS.get(entity, {})
        allowed = entity_config.get(operation, [])
        
        # Admin pode alterar campos adicionais em alguns casos
        if user_role == 'admin' and operation == 'update':
            # Admin pode alterar tipo de usuário, por exemplo
            if entity == 'usuario':
                allowed = allowed + ['tipo']
        
        # Filtrar dados
        filtered = {k: v for k, v in data.items() if k in allowed}
        
        # Log de campos removidos (tentativa de mass assignment)
        removed = set(data.keys()) - set(filtered.keys())
        if removed:
            current_app.logger.warning(
                f"[Mass Assignment] Campos removidos: {removed} "
                f"(entity={entity}, operation={operation}, user={session.get('usuario_id')})"
            )
        
        return filtered


def validate_input_schema(schema_class):
    """
    Decorador para validar entrada com Pydantic schema
    
    Args:
        schema_class: Classe Pydantic para validação
        
    Exemplo:
        from pydantic import BaseModel
        
        class CreateUserSchema(BaseModel):
            nome: str
            email: EmailStr
        
        @validate_input_schema(CreateUserSchema)
        def create_user():
            validated_data = request.validated_data
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Obter dados do request
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form.to_dict()
                
                # Validar com Pydantic
                validated = schema_class(**data)
                
                # Adicionar dados validados ao request
                request.validated_data = validated.dict()
                
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Erro de validação: {e}")
                
                if request.is_json:
                    return jsonify({
                        'error': True,
                        'message': 'Dados inválidos',
                        'details': str(e)
                    }), 400
                else:
                    abort(400, f"Dados inválidos: {e}")
        
        return decorated_function
    return decorator


__all__ = [
    'owns_resource',
    'FieldWhitelist',
    'validate_input_schema',
]

