"""
Configurações da Aplicação por Ambiente
========================================

Configuração simples e objetiva para Flask App Factory.

Autor: Sistema GERPED
Data: Outubro 2025
"""

import os
from datetime import timedelta, datetime


APP_ENV = os.getenv('FLASK_ENV', 'development').lower()


def _default_sqlite_uri(base_dir: str) -> str:
    return f"sqlite:///{os.path.abspath(os.path.join(base_dir, 'instance', 'sistema.db'))}"


def _resolve_secret_key(env: str) -> str:
    secret = os.getenv('SECRET_KEY')
    if secret:
        return secret
    if env in ('development', 'testing'):
        return 'dev-key-insecure-change-me'
    raise RuntimeError(
        'SECRET_KEY não configurada. Defina SECRET_KEY nas variáveis de ambiente para executar em produção.'
    )


def _sanitize_database_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        return ''
    placeholders = ('usuario', 'senha', 'porta', 'host', 'example.com')
    if any(token in url for token in placeholders):
        return ''
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


def _resolve_database_uri(base_dir: str, env: str, require_ssl: bool) -> str:
    db_url = _sanitize_database_url(os.getenv('DATABASE_URL', ''))
    if db_url:
        if db_url.lower().startswith('postgresql://') and require_ssl and 'sslmode=' not in db_url.lower():
            separator = '&' if '?' in db_url else '?'
            db_url = f"{db_url}{separator}sslmode=require"
        return db_url
    if env == 'production':
        raise RuntimeError('DATABASE_URL não configurada. Defina um banco PostgreSQL/MySQL antes do deploy.')
    return _default_sqlite_uri(base_dir)


class BaseConfig:
    """Configuração base compartilhada entre todos os ambientes"""
    
    # Diretório base
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    ENVIRONMENT = APP_ENV
    
    # Segurança - SECRET_KEY obrigatória
    SECRET_KEY = _resolve_secret_key(APP_ENV)
    
    # Banco de dados
    # SQLite requer /// para caminho relativo ou //// para caminho absoluto
    DATABASE_REQUIRE_SSL = os.getenv('DATABASE_REQUIRE_SSL', 'True').lower() == 'true'
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri(BASE_DIR, APP_ENV, DATABASE_REQUIRE_SSL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Sessão
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    _session_timeout_env = os.getenv('SESSION_INACTIVITY_TIMEOUT_MINUTES')
    try:
        _session_timeout_minutes = int(_session_timeout_env) if _session_timeout_env else 10
    except (TypeError, ValueError):
        _session_timeout_minutes = 10
    SESSION_INACTIVITY_TIMEOUT = timedelta(minutes=_session_timeout_minutes)
    SESSION_INACTIVITY_TIMEOUT_ADMIN = timedelta(hours=8)
    
    # Uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Logging
    LOG_DIR = os.path.join(BASE_DIR, 'instance', 'logs')
    LOG_LEVEL = 'INFO'
    
    # CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_SSL_STRICT = False
    
    # Cache (FASE 8)
    CACHE_TYPE = 'SimpleCache'  # SimpleCache para dev, Redis para prod
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutos
    CACHE_KEY_PREFIX = 'flask_cache_'
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "200 per hour"
    LOGIN_MAX_ATTEMPTS = int(os.getenv('LOGIN_MAX_ATTEMPTS', '5'))
    LOGIN_LOCKOUT_SECONDS = int(os.getenv('LOGIN_LOCKOUT_SECONDS', '300'))
    
    # Security Headers
    SECURITY_HEADERS_ENABLED = False
    
    # Google Vision (OCR)
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    OCR_MONTHLY_LIMIT = int(os.getenv('OCR_MONTHLY_LIMIT', '1000'))
    OCR_ENFORCE_LIMIT = os.getenv('OCR_ENFORCE_LIMIT', 'True').lower() == 'true'
    
    # RQ (Redis Queue) - Fase 7
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    RQ_ASYNC_ENABLED = os.getenv('RQ_ASYNC_ENABLED', 'True').lower() == 'true'
    COLETAS_LISTA_MAX_REGISTROS = int(os.getenv('COLETAS_LISTA_MAX_REGISTROS', '200'))
    COLETAS_RECIBO_TTL_HORAS = int(os.getenv('COLETAS_RECIBO_TTL_HORAS', '24'))

    # Go-live / Rollout control
    ROLLOUT_INTERNAL_ONLY_ENABLED = os.getenv('ROLLOUT_INTERNAL_ONLY_ENABLED', 'True').lower() == 'true'
    ROLLOUT_ALLOWED_ROLES = [
        role.strip().lower()
        for role in os.getenv('ROLLOUT_ALLOWED_ROLES', 'admin,financeiro').split(',')
        if role.strip()
    ]
    ROLLOUT_ALLOWED_USERS = [
        user.strip().lower()
        for user in os.getenv('ROLLOUT_ALLOWED_USERS', '').split(',')
        if user.strip()
    ]
    ROLLOUT_INTERNAL_DURATION_DAYS = int(os.getenv('ROLLOUT_INTERNAL_DURATION_DAYS', '7'))
    _rollout_start_env = os.getenv('ROLLOUT_START_DATE')
    try:
        ROLLOUT_START_DATE = datetime.fromisoformat(_rollout_start_env) if _rollout_start_env else None
    except ValueError:
        ROLLOUT_START_DATE = None
    del _rollout_start_env
    ROLLOUT_CONTROL = {
        'enabled': ROLLOUT_INTERNAL_ONLY_ENABLED,
        'allowed_roles': ROLLOUT_ALLOWED_ROLES,
        'allowed_users': ROLLOUT_ALLOWED_USERS,
        'internal_days': ROLLOUT_INTERNAL_DURATION_DAYS,
        'start_at': ROLLOUT_START_DATE,
        'blocked_message': os.getenv(
            'ROLLOUT_BLOCKED_MESSAGE',
            'Ambiente em fase de go-live controlado. Apenas usuários autorizados podem acessar no momento.'
        ),
        'alert_channel': os.getenv('ROLLOUT_ALERT_CHANNEL', 'logs'),
    }


class DevelopmentConfig(BaseConfig):
    """Configuração para desenvolvimento"""
    
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = 'DEBUG'
    RATELIMIT_DEFAULT = "500 per hour"
    
    # CSP em desenvolvimento - usar nonces mesmo em dev para testar
    CSP_DIRECTIVES = {
        "default-src": ["'self'"],
        "script-src": [
            "'self'",
            "'strict-dynamic'",  # Com nonce
            "https://cdn.jsdelivr.net",
            "https://code.jquery.com",
            "https://cdnjs.cloudflare.com"
        ],
        "style-src": [
            "'self'",
            "'unsafe-inline'",  # Mantém em dev por enquanto
            "https://cdn.jsdelivr.net",
            "https://fonts.googleapis.com",
            "https://www.gstatic.com"
        ],
        "img-src": ["'self'", "data:", "https:"],
        "font-src": ["'self'", "data:", "https://cdn.jsdelivr.net", "https://fonts.gstatic.com"],
        "connect-src": ["'self'", "https://cdn.jsdelivr.net"],
    }
    
    # Usar nonce em scripts (styles ainda com unsafe-inline em dev)
    CSP_NONCE_SOURCES = ["script-src"]


class TestingConfig(BaseConfig):
    """Configuração para testes"""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    CACHE_TYPE = 'NullCache'
    OCR_ENFORCE_LIMIT = False


class ProductionConfig(BaseConfig):
    """Configuração para produção"""
    
    DEBUG = False
    SESSION_COOKIE_SAMESITE = "Strict"
    WTF_CSRF_SSL_STRICT = True
    LOG_LEVEL = 'INFO'
    
    # Forçar HTTPS (pode ser sobrescrito via env)
    _force_https_env = os.getenv('FORCE_HTTPS')
    FORCE_HTTPS = True if _force_https_env is None else _force_https_env.lower() == 'true'
    PREFERRED_URL_SCHEME = 'https' if FORCE_HTTPS else 'http'
    
    # HSTS (HTTP Strict Transport Security)
    _hsts_env = os.getenv('HSTS_ENABLED')
    HSTS_ENABLED = (True if _hsts_env is None else _hsts_env.lower() == 'true') and FORCE_HTTPS
    HSTS_MAX_AGE = int(os.getenv('HSTS_MAX_AGE', '31536000'))  # 1 ano
    HSTS_INCLUDE_SUBDOMAINS = os.getenv('HSTS_INCLUDE_SUBDOMAINS', 'true').lower() == 'true'
    HSTS_PRELOAD = os.getenv('HSTS_PRELOAD', 'true').lower() == 'true'
    
    # Validação estrita em produção
    @classmethod
    def init_app(cls, app):
        """Validações adicionais para produção"""
        if cls.SECRET_KEY == "dev-key-insecure-change-me":
            raise RuntimeError("SECRET_KEY padrão detectada em produção! Configure SECRET_KEY.")
        if 'sqlite' in cls.SQLALCHEMY_DATABASE_URI.lower():
            import warnings
            warnings.warn("SQLite em produção não é recomendado. Use PostgreSQL ou MySQL.")
    
    # Headers de segurança habilitados em produção
    SECURITY_HEADERS_ENABLED = True
    
    # CSP rigoroso - sem unsafe-inline
    CSP_DIRECTIVES = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'strict-dynamic'"],  # nonce será injetado automaticamente
        'style-src': ["'self'", "https://www.gstatic.com"],  # nonce será injetado automaticamente  
        'img-src': ["'self'", 'data:', 'https:'],
        'font-src': ["'self'", 'data:'],
        'connect-src': ["'self'"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'frame-ancestors': ["'none'"],
        'form-action': ["'self'"],
        'upgrade-insecure-requests': [],
        'block-all-mixed-content': [],
    }
    
    # Aplicar nonce em scripts e styles
    CSP_NONCE_SOURCES = ["script-src", "style-src"]
    
    # Headers de segurança adicionais
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=(), payment=(), usb=()',
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Embedder-Policy': 'require-corp',
        'Cross-Origin-Resource-Policy': 'same-origin',
    }
    
    # Cache Redis (FASE 8)
    CACHE_TYPE = 'redis' if os.getenv('REDIS_URL') else 'SimpleCache'
    CACHE_REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_OPTIONS = {
        'socket_connect_timeout': 2,
        'socket_timeout': 2,
        'connection_pool_kwargs': {'max_connections': 50}
    }
    
    # Rate Limiting com Redis
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')


# Mapeamento de ambientes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """
    Retorna a configuração apropriada baseada no ambiente
    
    Args:
        env: Nome do ambiente ou None para auto-detectar via FLASK_ENV
    
    Returns:
        Classe de configuração apropriada
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    return config.get(env, config['default'])
