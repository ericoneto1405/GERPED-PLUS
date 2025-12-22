"""
Testes do Sistema RBAC (Role-Based Access Control)
===================================================

Testa autorização por papéis e controle de acesso.

Autor: Sistema GERPED
Data: Outubro 2025
"""

import pytest
from flask import session, jsonify
from meu_app import create_app, db
from meu_app.models import Usuario
from config import TestingConfig


@pytest.fixture
def app():
    """Cria aplicação de teste"""
    app = create_app(TestingConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Cliente de teste"""
    return app.test_client()


@pytest.fixture
def admin_user(app):
    """Usuário administrador"""
    with app.app_context():
        user = Usuario(
            nome='admin_test',
            senha_hash='',
            tipo='admin',
            acesso_clientes=True,
            acesso_produtos=True,
            acesso_pedidos=True,
            acesso_financeiro=True,
            acesso_logistica=True
        )
        user.set_senha('admin123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id  # Captura ID antes de sair do contexto
        db.session.expunge(user)  # Remove da sessão
    
    # Cria objeto simples com id
    class UserStub:
        def __init__(self, user_id):
            self.id = user_id
    
    return UserStub(user_id)


@pytest.fixture
def financeiro_user(app):
    """Usuário com role FINANCEIRO"""
    with app.app_context():
        user = Usuario(
            nome='financeiro_test',
            senha_hash='',
            tipo='comum',
            acesso_clientes=True,
            acesso_produtos=True,
            acesso_pedidos=True,
            acesso_financeiro=True,
            acesso_logistica=False
        )
        user.set_senha('financeiro123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        db.session.expunge(user)
    
    class UserStub:
        def __init__(self, user_id):
            self.id = user_id
    
    return UserStub(user_id)


@pytest.fixture
def logistica_user(app):
    """Usuário com role LOGISTICA"""
    with app.app_context():
        user = Usuario(
            nome='logistica_test',
            senha_hash='',
            tipo='comum',
            acesso_clientes=True,
            acesso_produtos=True,
            acesso_pedidos=True,
            acesso_financeiro=False,
            acesso_logistica=True
        )
        user.set_senha('logistica123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        db.session.expunge(user)
    
    class UserStub:
        def __init__(self, user_id):
            self.id = user_id
    
    return UserStub(user_id)


@pytest.fixture
def vendedor_user(app):
    """Usuário com role VENDEDOR"""
    with app.app_context():
        user = Usuario(
            nome='vendedor_test',
            senha_hash='',
            tipo='comum',
            acesso_clientes=True,
            acesso_produtos=True,
            acesso_pedidos=True,
            acesso_financeiro=False,
            acesso_logistica=False
        )
        user.set_senha('vendedor123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        db.session.expunge(user)
    
    class UserStub:
        def __init__(self, user_id):
            self.id = user_id
    
    return UserStub(user_id)


class TestRBACBasics:
    """Testes básicos do sistema RBAC"""
    
    def test_get_user_roles_admin(self, app, client, admin_user):
        """Admin deve ter role ADMIN"""
        from meu_app.auth.rbac import get_user_roles
        
        with client.session_transaction() as sess:
            sess['usuario_id'] = admin_user.id
            sess['usuario_tipo'] = 'admin'
        
        with app.test_request_context():
            # Copia sessão do client para o request context
            from flask import session as request_session
            request_session['usuario_id'] = admin_user.id
            request_session['usuario_tipo'] = 'admin'
            
            roles = get_user_roles()
            assert 'ADMIN' in roles
    
    def test_get_user_roles_financeiro(self, app, client, financeiro_user):
        """Usuário financeiro deve ter role FINANCEIRO"""
        from meu_app.auth.rbac import get_user_roles
        
        with app.test_request_context():
            from flask import session as request_session
            request_session['usuario_id'] = financeiro_user.id
            request_session['usuario_tipo'] = 'comum'
            request_session['acesso_financeiro'] = True
            request_session['acesso_clientes'] = True
            request_session['acesso_produtos'] = True
            request_session['acesso_pedidos'] = True
            
            roles = get_user_roles()
            assert 'FINANCEIRO' in roles
    
    def test_get_user_roles_not_authenticated(self, app):
        """Usuário não autenticado não tem roles"""
        from meu_app.auth.rbac import get_user_roles
        
        with app.app_context():
            roles = get_user_roles()
            assert len(roles) == 0


class TestRequiresRolesDecorator:
    """Testes do decorator @requires_roles"""
    
    def test_requires_admin_allows_admin(self, app, client, admin_user):
        """Admin deve acessar rota protegida por @requires_roles('ADMIN')"""
        from meu_app.auth.rbac import requires_roles
        
        @app.route('/test/admin')
        @requires_roles('ADMIN')
        def test_admin_route():
            return 'OK'
        
        # Login como admin
        with client.session_transaction() as sess:
            sess['usuario_id'] = admin_user.id
            sess['usuario_tipo'] = 'admin'
        
        response = client.get('/test/admin')
        assert response.status_code == 200
        assert b'OK' in response.data
    
    def test_requires_admin_blocks_non_admin(self, app, client, financeiro_user):
        """Não-admin deve ser bloqueado em rota ADMIN-only"""
        from meu_app.auth.rbac import requires_roles
        
        @app.route('/test/admin2')
        @requires_roles('ADMIN')
        def test_admin_route2():
            return 'OK'
        
        # Login como financeiro (não admin)
        with client.session_transaction() as sess:
            sess['usuario_id'] = financeiro_user.id
            sess['usuario_tipo'] = 'comum'
            sess['acesso_financeiro'] = True
        
        response = client.get('/test/admin2')
        assert response.status_code == 403
    
    def test_requires_financeiro_allows_admin(self, app, client, admin_user):
        """Admin deve acessar rota FINANCEIRO"""
        from meu_app.auth.rbac import requires_roles
        
        @app.route('/test/financeiro')
        @requires_roles('FINANCEIRO', 'ADMIN')
        def test_financeiro_route():
            return 'OK'
        
        with client.session_transaction() as sess:
            sess['usuario_id'] = admin_user.id
            sess['usuario_tipo'] = 'admin'
        
        response = client.get('/test/financeiro')
        assert response.status_code == 200
    
    def test_requires_financeiro_allows_financeiro_user(self, app, client, financeiro_user):
        """Usuário financeiro deve acessar rota FINANCEIRO"""
        from meu_app.auth.rbac import requires_roles
        
        @app.route('/test/financeiro2')
        @requires_roles('FINANCEIRO', 'ADMIN')
        def test_financeiro_route2():
            return 'OK'
        
        with client.session_transaction() as sess:
            sess['usuario_id'] = financeiro_user.id
            sess['usuario_tipo'] = 'comum'
            sess['acesso_financeiro'] = True
            sess['acesso_clientes'] = True
            sess['acesso_produtos'] = True
            sess['acesso_pedidos'] = True
        
        response = client.get('/test/financeiro2')
        assert response.status_code == 200
    
    def test_requires_financeiro_blocks_logistica(self, app, client, logistica_user):
        """Usuário logística NÃO deve acessar rota FINANCEIRO"""
        from meu_app.auth.rbac import requires_roles
        
        @app.route('/test/financeiro3')
        @requires_roles('FINANCEIRO', 'ADMIN')
        def test_financeiro_route3():
            return 'OK'
        
        with client.session_transaction() as sess:
            sess['usuario_id'] = logistica_user.id
            sess['usuario_tipo'] = 'comum'
            sess['acesso_logistica'] = True
            sess['acesso_clientes'] = True
            sess['acesso_produtos'] = True
            sess['acesso_pedidos'] = True
        
        response = client.get('/test/financeiro3')
        assert response.status_code == 403
    
    def test_requires_not_authenticated(self, app, client):
        """Usuário não autenticado deve ser redirecionado para login"""
        from meu_app.auth.rbac import requires_roles
        
        @app.route('/test/protected')
        @requires_roles('COMUM')
        def test_protected_route():
            return 'OK'
        
        response = client.get('/test/protected')
        assert response.status_code == 302  # Redirect
        assert b'login' in response.data.lower() or '/login' in response.location


class TestRBACJSON:
    """Testes de respostas JSON do RBAC"""
    
    def test_unauthorized_json_response(self, app, client):
        """Requisição JSON não autenticada deve retornar 401 JSON"""
        from meu_app.auth.rbac import requires_roles
        
        @app.route('/api/test/protected')
        @requires_roles('ADMIN')
        def test_api_protected():
            return jsonify({'data': 'secret'})
        
        response = client.get('/api/test/protected')
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] is True
        assert 'AuthenticationRequired' in data['type']
    
    def test_forbidden_json_response(self, app, client, vendedor_user):
        """Requisição JSON sem permissão deve retornar 403 JSON"""
        from meu_app.auth.rbac import requires_roles
        
        @app.route('/api/test/admin')
        @requires_roles('ADMIN')
        def test_api_admin():
            return jsonify({'data': 'secret'})
        
        with client.session_transaction() as sess:
            sess['usuario_id'] = vendedor_user.id
            sess['usuario_tipo'] = 'comum'
            sess['acesso_clientes'] = True
        
        response = client.get('/api/test/admin')
        assert response.status_code == 403
        data = response.get_json()
        assert data['error'] is True
        assert 'InsufficientPermissions' in data['type']


class TestRBACRoleMapping:
    """Testes de mapeamento de roles"""
    
    def test_admin_has_all_permissions(self, app, admin_user):
        """Admin deve ter todas as permissões"""
        from meu_app.auth.rbac import ROLE_PERMISSIONS_MAP
        
        admin_perms = ROLE_PERMISSIONS_MAP['ADMIN']
        assert 'acesso_financeiro' in admin_perms
        assert 'acesso_logistica' in admin_perms
        assert 'admin' in admin_perms
    
    def test_financeiro_has_financial_permissions(self, app):
        """FINANCEIRO deve ter permissões financeiras"""
        from meu_app.auth.rbac import ROLE_PERMISSIONS_MAP
        
        fin_perms = ROLE_PERMISSIONS_MAP['FINANCEIRO']
        assert 'acesso_financeiro' in fin_perms
        assert 'acesso_logistica' not in fin_perms
    
    def test_logistica_has_logistics_permissions(self, app):
        """LOGISTICA deve ter permissões logísticas"""
        from meu_app.auth.rbac import ROLE_PERMISSIONS_MAP
        
        log_perms = ROLE_PERMISSIONS_MAP['LOGISTICA']
        assert 'acesso_logistica' in log_perms
        assert 'acesso_financeiro' not in log_perms
    
    def test_has_any_role_true(self, app, client, financeiro_user):
        """has_any_role deve retornar True quando usuário tem o role"""
        from meu_app.auth.rbac import has_any_role
        
        with app.test_request_context():
            from flask import session as request_session
            request_session['usuario_id'] = financeiro_user.id
            request_session['usuario_tipo'] = 'comum'
            request_session['acesso_financeiro'] = True
            request_session['acesso_clientes'] = True
            request_session['acesso_produtos'] = True
            request_session['acesso_pedidos'] = True
            
            assert has_any_role(['FINANCEIRO']) is True
            assert has_any_role(['ADMIN', 'FINANCEIRO']) is True
    
    def test_has_any_role_false(self, app, client, vendedor_user):
        """has_any_role deve retornar False quando usuário não tem o role"""
        from meu_app.auth.rbac import has_any_role
        
        with client.session_transaction() as sess:
            sess['usuario_id'] = vendedor_user.id
            sess['usuario_tipo'] = 'comum'
            sess['acesso_clientes'] = True
        
        with app.app_context():
            assert has_any_role(['FINANCEIRO']) is False
            assert has_any_role(['LOGISTICA']) is False
