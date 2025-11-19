"""
Testes de Contrato (Snapshot Testing)
======================================

Testes que validam o formato de resposta das APIs permanece consistente.
Previne breaking changes não intencionais em contratos de API.

Autor: Sistema GERPED - Fase 9
"""

import pytest
from meu_app import create_app, db
from meu_app.models import Usuario, Cliente, Produto, Pedido
from config import TestingConfig


@pytest.fixture
def app():
    """Cria aplicação para testes"""
    app = create_app(TestingConfig)
    
    with app.app_context():
        db.create_all()
        
        # Criar usuário de teste
        usuario = Usuario(
            nome='admin',
            senha_hash='',
            tipo='admin',
            acesso_clientes=True,
            acesso_produtos=True,
            acesso_pedidos=True,
            acesso_financeiro=True,
            acesso_logistica=True
        )
        usuario.set_senha('admin123')
        db.session.add(usuario)
        
        # Criar cliente de teste
        cliente = Cliente(
            nome='Cliente Teste',
            fantasia='Cliente Fantasia',
            cpf_cnpj='12345678901'
        )
        db.session.add(cliente)
        
        # Criar produto de teste
        produto = Produto(
            nome='Produto Teste',
            codigo_interno='PROD001',
            preco_medio_compra=10.50
        )
        db.session.add(produto)
        
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Cliente de teste"""
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    """Cliente autenticado"""
    # Login
    client.post('/login', data={
        'nome': 'admin',
        'senha': 'admin123'
    }, follow_redirects=True)
    
    return client


class TestAPIContracts:
    """Testes de contrato de APIs"""
    
    def test_healthz_contract(self, client, snapshot):
        """
        Snapshot do contrato de /healthz
        
        Garante que estrutura da resposta não muda sem intenção.
        """
        response = client.get('/healthz')
        data = response.get_json()
        
        # Remover timestamp (varia)
        data.pop('timestamp', None)
        
        # Validar estrutura
        assert data == snapshot
    
    def test_readiness_contract(self, client, snapshot):
        """
        Snapshot do contrato de /readiness
        """
        response = client.get('/readiness')
        data = response.get_json()
        
        # Remover timestamp
        data.pop('timestamp', None)
        
        # Validar estrutura de checks
        assert set(data.keys()) == {'status', 'checks'}
        assert 'database' in data['checks']
        assert 'cache' in data['checks']
    
    def test_metrics_contract_format(self, client):
        """
        Valida formato de métricas Prometheus
        """
        response = client.get('/metrics')
        
        assert response.status_code == 200
        assert response.content_type == 'text/plain; charset=utf-8'
        
        # Verificar que contém métricas esperadas
        text = response.data.decode('utf-8')
        assert 'http_requests_total' in text
        assert 'http_request_duration_seconds' in text
    
    def test_error_response_contract(self, client, snapshot):
        """
        Snapshot do formato de erro padrão
        """
        response = client.get('/rota-inexistente')
        data = response.get_json()
        
        # Remover timestamp
        data.pop('timestamp', None)
        
        # Estrutura de erro padrão
        assert 'error' in data
        assert 'message' in data
        assert 'type' in data
        assert data['error'] is True


class TestBusinessContracts:
    """Testes de contrato de operações de negócio"""
    
    def test_cliente_list_structure(self, authenticated_client):
        """
        Valida estrutura de listagem de clientes
        """
        response = authenticated_client.get('/clientes/')
        
        # Deve retornar HTML (não API JSON neste caso)
        assert response.status_code == 200
        assert b'Cliente' in response.data or response.content_type == 'text/html'
    
    def test_produto_list_structure(self, authenticated_client):
        """
        Valida estrutura de listagem de produtos
        """
        response = authenticated_client.get('/produtos/')
        
        assert response.status_code == 200
        assert b'Produto' in response.data or response.content_type == 'text/html'


class TestResponseTimeContract:
    """
    Testes de contrato de performance
    
    Garante que endpoints críticos respondem dentro do SLA.
    """
    
    def test_healthz_response_time(self, client):
        """Healthcheck deve responder em < 100ms"""
        import time
        
        start = time.time()
        response = client.get('/healthz')
        duration = (time.time() - start) * 1000  # ms
        
        assert response.status_code == 200
        assert duration < 100, f"Healthcheck muito lento: {duration}ms"
    
    def test_readiness_response_time(self, client):
        """Readiness deve responder em < 500ms"""
        import time
        
        start = time.time()
        response = client.get('/readiness')
        duration = (time.time() - start) * 1000
        
        assert response.status_code in [200, 503]
        assert duration < 500, f"Readiness muito lento: {duration}ms"

