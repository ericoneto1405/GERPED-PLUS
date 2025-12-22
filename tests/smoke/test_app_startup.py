import pytest

from config import DevelopmentConfig
from meu_app import create_app


@pytest.mark.smoke
def test_app_startup(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app = create_app(DevelopmentConfig)

    assert app is not None
    assert app.config.get("SQLALCHEMY_DATABASE_URI")
    assert "main" in app.blueprints
