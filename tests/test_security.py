import os
import re

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from config import TestingConfig  # noqa: E402

try:
    from meu_app import create_app, db  # noqa: E402
    from meu_app.models import Usuario  # noqa: E402
except ModuleNotFoundError as exc:  # pragma: no cover - handled via skip
    pytest.skip(
        f"Dependência ausente para executar testes de segurança: {exc.name}",
        allow_module_level=True,
    )


class SecurityTestConfig(TestingConfig):
    WTF_CSRF_ENABLED = True
    RATELIMIT_ENABLED = True
    SECURITY_HEADERS_ENABLED = True
    RATELIMIT_DEFAULT = "100 per minute"
    LOGIN_RATE_LIMIT = "3 per minute"
    TALISMAN_FORCE_HTTPS = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"


@pytest.fixture
def security_app():
    app = create_app(SecurityTestConfig)
    app.config.update(SESSION_COOKIE_SAMESITE="Strict")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _extract_csrf_token(response_data: bytes) -> str:
    html = response_data.decode("utf-8")
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if not match:
        raise AssertionError("CSRF token not found in response HTML")
    return match.group(1)


def test_login_form_contains_csrf_token(security_app):
    client = security_app.test_client()

    response = client.get("/login")

    assert response.status_code == 200
    assert b'name="csrf_token"' in response.data


def test_login_without_csrf_rejected(security_app):
    client = security_app.test_client()

    response = client.post("/login", data={"usuario": "foo", "senha": "bar"})

    assert response.status_code == 400


def test_login_rate_limit_enforced(security_app):
    client = security_app.test_client()

    statuses = []
    for _ in range(4):
        token = _extract_csrf_token(client.get("/login").data)
        response = client.post(
            "/login",
            data={"usuario": "foo", "senha": "bar", "csrf_token": token},
        )
        statuses.append(response.status_code)

    assert 429 in statuses
    assert statuses[-1] == 429


def test_security_headers_present(security_app):
    client = security_app.test_client()

    response = client.get("/login")

    assert response.status_code == 200
    assert response.headers.get("X-Frame-Options") == "DENY"

    csp = response.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp


def test_session_cookie_flags(security_app):
    client = security_app.test_client()

    with security_app.app_context():
        usuario = Usuario(
            nome="tester",
            senha_hash="",
            tipo="admin",
            acesso_clientes=True,
            acesso_produtos=True,
            acesso_pedidos=True,
            acesso_financeiro=True,
            acesso_logistica=True,
        )
        usuario.set_senha("StrongPass123!")
        db.session.add(usuario)
        db.session.commit()

    token = _extract_csrf_token(client.get("/login").data)
    response = client.post(
        "/login",
        data={"usuario": "tester", "senha": "StrongPass123!", "csrf_token": token},
        follow_redirects=False,
    )

    assert response.status_code in {302, 303}

    cookies = response.headers.getlist("Set-Cookie")
    assert cookies, "Expected a session cookie to be issued"

    cookie_name = security_app.config.get("SESSION_COOKIE_NAME", "session")
    session_cookie = next((c for c in cookies if cookie_name in c), "")
    assert "Secure" in session_cookie
    assert "HttpOnly" in session_cookie
    assert "SameSite=Strict" in session_cookie
