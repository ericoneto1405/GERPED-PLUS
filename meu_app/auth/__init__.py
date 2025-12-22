"""Sistema de autenticação e autorização"""

from .rbac import (
    requires_roles,
    requires_admin,
    requires_financeiro,
    requires_logistica,
    requires_vendedor,
    get_user_roles,
    has_any_role,
    ROLE_PERMISSIONS_MAP
)

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
