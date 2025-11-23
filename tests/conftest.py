import pytest
from config import TestingConfig
from meu_app import create_app


class PytestConfig(TestingConfig):
    """Configuração de teste compartilhada para fixtures pytest-flask."""
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}


@pytest.fixture
def app():
    """Instância da aplicação Flask usada pelos testes de integração."""
    app = create_app(PytestConfig)
    yield app
