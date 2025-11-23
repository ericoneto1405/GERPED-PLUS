"""
Configuração OpenAPI/Swagger
=============================

Sistema de documentação interativa de APIs usando Flasgger.

Endpoint: /docs - Swagger UI interativo
Endpoint: /apispec - OpenAPI JSON

Autor: Sistema GERPED - Fase 10
"""

from flasgger import Swagger


# Configuração do Swagger
SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,  # Incluir todas as rotas
            "model_filter": lambda tag: True,  # Incluir todos os models
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs",  # Rota principal da documentação
}

# Template do Swagger
SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "Sistema GERPED API",
        "description": """
# Sistema de Gestão Empresarial GERPED

API REST completa para gestão de pedidos, vendas, financeiro e logística.

## Funcionalidades

- 👥 **Clientes** - CRUD completo de clientes
- 📦 **Produtos** - Gestão de catálogo e estoque
- 🛒 **Pedidos** - Criação e acompanhamento de pedidos
- 💰 **Financeiro** - Pagamentos e OCR de recibos
- 📊 **Apuração** - Relatórios financeiros mensais
- 🚚 **Coletas** - Logística e geração de recibos PDF
- 👤 **Vendedor** - Dashboard e análises

## Autenticação

A maioria dos endpoints requer autenticação via sessão.

1. Fazer login em `/login`
2. Sessão é mantida automaticamente
3. Logout em `/logout`

## Rate Limiting

- **Padrão**: 200 requisições/hora
- **Login**: 10 requisições/minuto

## Observabilidade

- **Métricas**: `GET /metrics` (Prometheus)
- **Healthcheck**: `GET /healthz` (Liveness)
- **Readiness**: `GET /readiness` (Readiness)

## Performance

- Cache Redis em endpoints de leitura
- TTL configurável por endpoint
- Invalidação automática por eventos
        """,
        "version": "2.0.0",
        "termsOfService": "",
        "contact": {
            "name": "Sistema GERPED",
            "email": "suporte@sistema-gerped.com",
        },
        "license": {
            "name": "MIT",
        },
    },
    "host": "localhost:5004",
    "basePath": "/",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "SessionAuth": {
            "type": "apiKey",
            "in": "cookie",
            "name": "session",
            "description": "Autenticação via sessão Flask. Faça login primeiro.",
        }
    },
    "security": [{"SessionAuth": []}],
    "tags": [
        {
            "name": "Health",
            "description": "Endpoints de monitoramento e saúde",
        },
        {
            "name": "Auth",
            "description": "Autenticação e autorização",
        },
        {
            "name": "Clientes",
            "description": "Gestão de clientes",
        },
        {
            "name": "Produtos",
            "description": "Gestão de produtos e estoque",
        },
        {
            "name": "Pedidos",
            "description": "Criação e gestão de pedidos",
        },
        {
            "name": "Financeiro",
            "description": "Pagamentos e OCR",
        },
        {
            "name": "Apuração",
            "description": "Relatórios financeiros mensais",
        },
        {
            "name": "Vendedor",
            "description": "Dashboard e análises para vendedores",
        },
        {
            "name": "Coletas",
            "description": "Logística e geração de recibos",
        },
    ],
}


def init_swagger(app):
    """
    Inicializa Swagger/OpenAPI para documentação interativa.
    
    Args:
        app: Instância Flask
        
    Adiciona:
        - GET /docs - Swagger UI
        - GET /apispec.json - OpenAPI spec
    """
    swagger = Swagger(
        app,
        config=SWAGGER_CONFIG,
        template=SWAGGER_TEMPLATE,
        parse=True,
        sanitizer=None,
    )
    
    app.logger.info(
        'Swagger UI inicializado',
        extra={
            'docs_url': '/docs',
            'spec_url': '/apispec.json'
        }
    )
    
    return swagger

