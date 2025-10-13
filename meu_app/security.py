"""
Configuração de segurança base da aplicação Flask.

Centraliza CSRF global, rate limiting, headers de segurança e nonce para CSP.
"""
from __future__ import annotations

import secrets
from typing import Iterable, List, Optional

from flask import current_app, g, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError


csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
_talisman: Optional[Talisman] = None

DEFAULT_CSP = {
    "default-src": ["'self'"],
    "script-src": ["'self'"],
    "style-src": ["'self'", "'unsafe-inline'"],
    "img-src": ["'self'", "data:"],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
    "frame-ancestors": ["'none'"],
}


def setup_security(app) -> None:
    """
    Inicializa proteções base (CSRF, rate limiting, headers e nonce).
    Deve ser chamada uma única vez durante a criação da aplicação.
    """
    _configure_session_defaults(app)
    _configure_csrf(app)
    _configure_rate_limiting(app)
    _configure_talisman(app)
    _register_nonce_context_processor(app)

    lifetime = app.config.get("PERMANENT_SESSION_LIFETIME")
    if lifetime:
        app.permanent_session_lifetime = lifetime


def _configure_session_defaults(app) -> None:
    """Garante os atributos mínimos dos cookies de sessão."""
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    if app.debug or app.testing:
        app.config.setdefault("SESSION_COOKIE_SECURE", False)
    else:
        app.config.setdefault("SESSION_COOKIE_SECURE", True)


def _configure_csrf(app) -> None:
    """Ativa CSRF global e trata falhas."""
    csrf.init_app(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error: CSRFError):
        current_app.logger.warning(
            "Bloqueio CSRF: %s (rota %s, ip %s)",
            error.description,
            request.path,
            request.remote_addr,
        )

        if request.is_json or request.accept_mimetypes["application/json"] > 0:
            return (
                jsonify(
                    {
                        "error": True,
                        "type": "CSRFError",
                        "message": error.description,
                    }
                ),
                400,
            )

        return (
            render_template(
                "csrf_error.html",
                message="Sessão expirada ou formulário inválido. Atualize a página e tente novamente.",
            ),
            400,
        )


def _configure_rate_limiting(app) -> None:
    """Inicializa o Flask-Limiter com as configurações do app."""
    storage_uri = app.config.get("RATELIMIT_STORAGE_URL", "memory://")
    default_limits = _coerce_limits(app.config.get("RATELIMIT_DEFAULT", "200 per hour"))
    enabled = app.config.get("RATELIMIT_ENABLED", True)
    
    # FIX: Flask-Limiter 4.0+ mudou a API
    # Configurar storage_uri via propriedade antes de init_app
    limiter.storage_uri = storage_uri
    
    # Inicializar com app (sem storage_uri como parâmetro)
    limiter.init_app(app)
    
    # Configurar após init
    limiter.enabled = enabled
    if default_limits:
        limiter._default_limits = default_limits

    app.config.setdefault("LOGIN_RATE_LIMIT", "10 per minute")


def _configure_talisman(app) -> None:
    """Aplica os headers de segurança via Flask-Talisman."""
    global _talisman  # pylint: disable=global-statement

    csp = app.config.get("CSP_DIRECTIVES") or DEFAULT_CSP
    nonce_directives = app.config.get("CSP_NONCE_SOURCES", ["script-src"])

    # Configurações de HTTPS e HSTS
    force_https = app.config.get("FORCE_HTTPS", False) if not (app.debug or app.testing) else False
    hsts_enabled = app.config.get("HSTS_ENABLED", False) if not app.testing else False
    hsts_max_age = app.config.get("HSTS_MAX_AGE", 31536000) if hsts_enabled else None
    hsts_include_subdomains = app.config.get("HSTS_INCLUDE_SUBDOMAINS", True)
    hsts_preload = app.config.get("HSTS_PRELOAD", True)

    _talisman = Talisman(
        app,
        content_security_policy=csp,
        content_security_policy_nonce_in=nonce_directives,
        frame_options="DENY",
        referrer_policy="strict-origin-when-cross-origin",
        force_https=force_https,
        strict_transport_security=hsts_enabled,
        strict_transport_security_max_age=hsts_max_age,
        strict_transport_security_include_subdomains=hsts_include_subdomains if hsts_enabled else False,
        strict_transport_security_preload=hsts_preload if hsts_enabled else False,
        session_cookie_secure=app.config.get("SESSION_COOKIE_SECURE", True),
        session_cookie_http_only=True,
        content_security_policy_report_uri=None,
        feature_policy={
            'geolocation': "'none'",
            'microphone': "'none'",
            'camera': "'none'",
            'payment': "'none'",
            'usb': "'none'",
        }
    )


def _register_nonce_context_processor(app) -> None:
    """Disponibiliza o nonce para todos os templates."""

    def _get_nonce() -> str:
        talisman_nonce = getattr(request, "csp_nonce", None)
        if talisman_nonce:
            return talisman_nonce
        if not hasattr(g, "_csp_nonce"):
            g._csp_nonce = secrets.token_urlsafe(16)  # type: ignore[attr-defined]
        return g._csp_nonce  # type: ignore[attr-defined]

    @app.context_processor
    def inject_nonce():
        return {"nonce": _get_nonce()}


def _coerce_limits(raw_limits) -> List[str]:
    """Normaliza limites que podem vir em string ou iterável."""
    if not raw_limits:
        return []
    if isinstance(raw_limits, str):
        return [lim.strip() for lim in raw_limits.split(";") if lim.strip()]
    if isinstance(raw_limits, Iterable):
        return [str(lim).strip() for lim in raw_limits if str(lim).strip()]
    return []


__all__ = ["csrf", "limiter", "setup_security"]
