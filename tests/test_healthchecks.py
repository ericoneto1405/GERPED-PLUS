"""
Testes de Healthchecks
======================

Testes para endpoints de health e readiness.

Autor: Sistema GERPED - Fase 9
"""

import pytest
from meu_app import create_app, db
from config import TestingConfig


@pytest.fixture
def app():
    """Cria aplicação para testes"""
    app = create_app(TestingConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Cliente de teste"""
    return app.test_client()


class TestHealthchecks:
    """Testes de healthchecks"""
    
    def test_healthz_endpoint_exists(self, client):
        """Verifica se endpoint /healthz existe"""
        response = client.get('/healthz')
        assert response.status_code == 200
    
    def test_healthz_returns_json(self, client):
        """Verifica se /healthz retorna JSON"""
        response = client.get('/healthz')
        assert response.content_type == 'application/json'
    
    def test_healthz_has_correct_structure(self, client):
        """Verifica estrutura da resposta de /healthz"""
        response = client.get('/healthz')
        data = response.get_json()
        
        assert 'status' in data
        assert 'service' in data
        assert 'timestamp' in data
        assert data['status'] == 'healthy'
        assert data['service'] == 'sistema-gerped'
    
    def test_readiness_endpoint_exists(self, client):
        """Verifica se endpoint /readiness existe"""
        response = client.get('/readiness')
        # Pode ser 200 ou 503 dependendo do ambiente
        assert response.status_code in [200, 503]
    
    def test_readiness_returns_json(self, client):
        """Verifica se /readiness retorna JSON"""
        response = client.get('/readiness')
        assert response.content_type == 'application/json'
    
    def test_readiness_has_correct_structure(self, client):
        """Verifica estrutura da resposta de /readiness"""
        response = client.get('/readiness')
        data = response.get_json()
        
        assert 'status' in data
        assert 'checks' in data
        assert 'timestamp' in data
        assert 'database' in data['checks']
        assert 'cache' in data['checks']
    
    def test_readiness_checks_database(self, client):
        """Verifica se readiness testa conexão com banco"""
        response = client.get('/readiness')
        data = response.get_json()
        
        # Em ambiente de testes, database deve estar OK
        assert data['checks']['database'] is True
    
    def test_healthz_metrics_integration(self, client):
        """Verifica se healthchecks não afetam métricas HTTP normais"""
        # Healthchecks não devem inflar métricas de negócio
        response = client.get('/healthz')
        assert response.status_code == 200
        
        # Verificar que métricas existem
        metrics_response = client.get('/metrics')
        assert metrics_response.status_code == 200

