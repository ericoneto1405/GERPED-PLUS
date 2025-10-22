"""
Aplicação Flask - Sistema SAP
==============================

App Factory pattern com suporte a múltiplos ambientes e extensões.

Autor: Sistema SAP
Data: Outubro 2025
"""

import logging
import os
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_caching import Cache as FlaskCache
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .security import csrf, limiter, setup_security

# Carregar variáveis de ambiente
load_dotenv()

# Inicializar extensões (sem app ainda)
db = SQLAlchemy()
migrate = Migrate()
flask_cache = FlaskCache()  # Renomeado para evitar conflito com meu_app/cache.py
login_manager = LoginManager()


def setup_api_docs(app):
    """
    Configura documentação OpenAPI/Swagger (FASE 10)
    
    Adiciona:
    - GET /docs - Swagger UI interativo
    - GET /apispec.json - OpenAPI specification
    
    FIX #6: Módulo esperado (verificado):
    - meu_app/api/docs.py (init_swagger)
    """
    from .api.docs import init_swagger
    
    init_swagger(app)
    
    app.logger.info('Documentação OpenAPI disponível em /docs')


def create_app(config_class=None):
    """
    Função fábrica para criar a aplicação Flask
    
    Args:
        config_class: Classe de configuração a ser usada.
    
    Returns:
        Flask: Instância configurada da aplicação
    """
    app = Flask(__name__)
    
    # Carregar configuração
    if config_class is None:
        from config import get_config
        config_class = get_config()
    app.config.from_object(config_class)
    
    # Inicializar extensões
    initialize_extensions(app)
    
    # FASE 6: Configurar observabilidade (logging estruturado, métricas, middleware)
    setup_observability(app)
    
    # Registrar error handlers
    register_error_handlers(app)
    
    # Registrar filtros personalizados
    register_custom_filters(app)
    
    # Registrar blueprints
    register_blueprints(app)
    
    # FASE 10: Documentação OpenAPI/Swagger
    setup_api_docs(app)
    
    # Warm-up do OCR (opcional)
    warmup_ocr(app)
    
    # Log de inicialização
    app.logger.info('=' * 60)
    app.logger.info('Aplicação SAP iniciada')
    app.logger.info(f'Ambiente: {app.config.get("ENV", "development")}')
    app.logger.info(f'Debug: {app.debug}')
    
    # FIX #2: Usar .get() para evitar KeyError
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
    app.logger.info(f'Database: {db_uri[:50]}...')
    app.logger.info('=' * 60)
    
    return app


def initialize_extensions(app):
    """
    Inicializa todas as extensões Flask
    
    Extensões registradas:
    - DB (SQLAlchemy)
    - Migrate (Flask-Migrate/Alembic)
    - CSRF (Flask-WTF)
    - LoginManager (Flask-Login)
    - Cache (Flask-Caching)
    - Limiter (Flask-Limiter)
    - Talisman (Flask-Talisman, condicional)
    """
    # Database
    db.init_app(app)
    
    # Migrations (Alembic via Flask-Migrate)
    migrate.init_app(app, db)
    
    # CSRF Protection (via meu_app.security)
    
    # LoginManager
    login_manager.init_app(app)
    # FIX #1: login_view aponta para 'main.login' (verificado: BP='main' existe em routes.py)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    # User loader para LoginManager
    @login_manager.user_loader
    def load_user(user_id):
        from .models import Usuario
        # FIX #3: Migrar para db.session.get() (SQLAlchemy 2.x)
        return db.session.get(Usuario, int(user_id))
    
    # Cache (Flask-Caching)
    flask_cache.init_app(app)
    
    # Segurança (CSRF, Limiter, Talisman)
    setup_security(app)
    
    # Aplicar headers de segurança adicionais
    @app.after_request
    def apply_security_headers(response):
        """Aplica headers de segurança adicionais configurados"""
        if app.config.get('SECURITY_HEADERS'):
            for header, value in app.config['SECURITY_HEADERS'].items():
                response.headers[header] = value
        
        # Remover headers que expõem informações do servidor
        response.headers.pop('Server', None)
        response.headers.pop('X-Powered-By', None)
        
        # Cache-Control para rotas autenticadas
        if request.endpoint and not request.endpoint.startswith('static'):
            from flask_login import current_user
            if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
        
        return response
    
    @app.before_request
    def enforce_session_inactivity_timeout():
        """Encerra sessão após período configurado de inatividade."""
        timeout = app.config.get('SESSION_INACTIVITY_TIMEOUT')
        if not timeout:
            return
        
        # Ignorar rotas públicas ou estáticas
        if request.endpoint in (None, 'static') or (request.endpoint and request.endpoint.endswith('.static')):
            return
        
        if 'usuario_id' not in session:
            return
        
        now = datetime.utcnow()
        usuario_tipo = (session.get('usuario_tipo') or '').lower()
        if usuario_tipo == 'admin':
            session['ultimo_acesso'] = now.isoformat()
            session.permanent = True
            session.modified = True
            return
        
        last_seen_raw = session.get('ultimo_acesso')
        last_seen = None
        if last_seen_raw:
            try:
                last_seen = datetime.fromisoformat(last_seen_raw)
            except ValueError:
                app.logger.warning("Valor inválido em session['ultimo_acesso']; resetando controle de inatividade.")
        
        if last_seen and now - last_seen > timeout:
            from flask_login import logout_user  # Import lazy para evitar ciclos
            app.logger.info("Sessão expirada por inatividade para usuário_id=%s", session.get('usuario_id'))
            logout_user()
            session.clear()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.path.startswith('/api/') or \
               request.headers.get('Accept') == 'application/json':
                return jsonify({
                    'error': True,
                    'message': 'Sessão expirada por inatividade. Faça login novamente.',
                    'type': 'SessionExpired',
                    'timestamp': now.isoformat()
                }), 401
            
            return redirect(url_for('main.login', session_expired=1))
        
        session['ultimo_acesso'] = now.isoformat()
        session.permanent = True
        session.modified = True
    
    # RQ (Redis Queue) para processamento assíncrono - Fase 7
    try:
        from .queue import init_queue
        init_queue(app)
    except Exception as e:
        app.logger.warning(f"⚠️ RQ não inicializado: {e}")


def setup_observability(app):
    """
    Configura o sistema completo de observabilidade (FASE 6)
    
    Componentes:
    - Logging estruturado JSON com request_id
    - Métricas Prometheus
    - Middleware de rastreamento de requests
    
    FIX #6: Módulos esperados (verificado):
    - meu_app/obs/__init__.py (exporta setup_structured_logging, init_metrics, setup_request_tracking)
    - meu_app/obs/logging.py (CustomJsonFormatter)
    - meu_app/obs/metrics.py (Prometheus metrics)
    - meu_app/obs/middleware.py (Request tracking)
    """
    from .obs import setup_structured_logging, init_metrics, setup_request_tracking
    
    # 1. Logging estruturado JSON
    setup_structured_logging(app)
    
    # 2. Métricas Prometheus
    init_metrics(app)
    
    # 3. Middleware de rastreamento
    setup_request_tracking(app)


def register_error_handlers(app):
    """Registra manipuladores de erro globais"""
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Manipulador global de exceções"""
        # Log detalhado
        app.logger.error(f'Erro não tratado: {str(e)}')
        app.logger.error(f'Traceback: {traceback.format_exc()}')
        app.logger.error(f'URL: {request.url}')
        app.logger.error(f'Método: {request.method}')
        app.logger.error(f'IP: {request.remote_addr}')
        
        # FIX #4: Respeitar Accept header (JSON vs HTML)
        wants_json = (
            request.is_json
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or request.path.startswith('/api/')
            or request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json'
        )
        
        if wants_json:
            return jsonify({
                'error': True,
                'message': 'Erro interno do servidor' if not app.debug else str(e),
                'type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # Para requisições HTML, renderizar template 500.html
        try:
            return render_template('500.html', error=str(e) if app.debug else None), 500
        except Exception:
            # Fallback se template não existir
            return f'<h1>500 - Erro Interno</h1><p>Ocorreu um erro inesperado.</p>', 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Manipulador para erros 404"""
        app.logger.warning(f'Página não encontrada: {request.url}')
        
        # FIX #4: Respeitar Accept header (JSON vs HTML)
        wants_json = (
            request.is_json
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or request.path.startswith('/api/')
            or request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json'
        )
        
        if wants_json:
            return jsonify({
                'error': True,
                'message': 'Recurso não encontrado',
                'type': 'NotFound',
                'timestamp': datetime.now().isoformat()
            }), 404
        
        # Para requisições HTML, renderizar template 404.html
        try:
            return render_template('404.html'), 404
        except Exception:
            # Fallback se template não existir
            return '<h1>404 - Página Não Encontrada</h1>', 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Manipulador para erros 403 (acesso negado)"""
        app.logger.warning(f'Acesso negado: {request.url} - IP: {request.remote_addr}')
        
        # Se for JSON/API, retornar JSON
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({
                'error': True,
                'message': 'Acesso negado. Você não tem permissão para acessar este recurso.',
                'type': 'Forbidden',
                'timestamp': datetime.now().isoformat()
            }), 403
        
        # Retornar template 403 amigável
        return render_template('403.html'), 403
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Manipulador para rate limit excedido"""
        app.logger.warning(f'Rate limit excedido: {request.url} - IP: {request.remote_addr}')
        
        return jsonify({
            'error': True,
            'message': 'Muitas requisições. Tente novamente mais tarde.',
            'type': 'RateLimitExceeded',
            'timestamp': datetime.now().isoformat()
        }), 429


def register_custom_filters(app):
    """Registra filtros personalizados para os templates"""
    
    @app.template_filter('currency_brl')
    def currency_brl_filter(value):
        """Filtro para formatação de moeda brasileira"""
        if value is None or value == '':
            return 'R$ 0,00'
        
        try:
            if isinstance(value, str):
                value = float(value.replace(',', '.'))
            
            formatted = "{:,.2f}".format(float(value))
            formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
            
            return f'R$ {formatted}'
        except (ValueError, TypeError):
            return 'R$ 0,00'
    
    @app.template_filter('number_brl')
    def number_brl_filter(value):
        """Filtro para formatação de números no padrão brasileiro"""
        if value is None or value == '':
            return '0,00'
        
        try:
            if isinstance(value, str):
                value = float(value.replace(',', '.'))
            
            formatted = "{:,.2f}".format(float(value))
            formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
            
            return formatted
        except (ValueError, TypeError):
            return '0,00'


def register_blueprints(app):
    """
    Registra todos os blueprints da aplicação (por domínio)
    
    FIX #5: url_prefix definido nos módulos (verificado):
    - main              → (root)
    - produtos          → /produtos
    - clientes          → /clientes
    - pedidos           → /pedidos
    - usuarios          → /usuarios
    - estoques          → /estoques
    - financeiro        → /financeiro
    - coletas           → /coletas
    - apuracao          → /apuracao
    - log_atividades    → /log_atividades
    - vendedor          → /vendedor
    - leitura_notas     → /leitura-notas
    
    Garantia: prefixos definidos nos módulos (única fonte de verdade)
    """
    # Blueprint principal (root - login, painel, logout)
    from . import routes
    app.register_blueprint(routes.bp)
    
    # Blueprints de domínio (url_prefix definido em cada módulo)
    from .produtos import produtos_bp
    from .clientes import clientes_bp
    from .pedidos import pedidos_bp
    from .usuarios import usuarios_bp
    from .estoques import estoques_bp
    from .financeiro import financeiro_bp
    from .coletas import coletas_bp
    from .apuracao import apuracao_bp
    from .log_atividades import log_atividades_bp
    from .vendedor import vendedor_bp
    from .jobs.routes import bp as jobs_bp  # Fase 7
    from .leitura_notas import leitura_notas_bp
    from .necessidade_compra import necessidade_compra_bp
    
    # Registrar blueprints (ordem não importa, prefixos evitam colisão)
    app.register_blueprint(produtos_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(estoques_bp)
    app.register_blueprint(financeiro_bp)
    app.register_blueprint(coletas_bp)
    app.register_blueprint(apuracao_bp)
    app.register_blueprint(log_atividades_bp)
    app.register_blueprint(vendedor_bp)
    app.register_blueprint(leitura_notas_bp)
    app.register_blueprint(jobs_bp)  # Fase 7
    app.register_blueprint(necessidade_compra_bp)  # Análise de Compra
    
    app.logger.info(f'Blueprints registrados: {len(app.blueprints)}')


def warmup_ocr(app):
    """Warm-up opcional do OCR para reduzir latência"""
    try:
        from .financeiro.config import FinanceiroConfig
        if getattr(FinanceiroConfig, 'OCR_WARMUP', False):
            from .financeiro.ocr_service import OcrService
            OcrService._get_reader()
            app.logger.info('OCR warm-up concluído')
    except Exception as e:
        app.logger.warning(f'OCR warm-up falhou: {e}')
