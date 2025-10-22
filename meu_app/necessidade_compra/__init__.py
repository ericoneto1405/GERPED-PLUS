"""
Módulo de Análise de Necessidade de Compra
Analisa estoque, pedidos e sugere compras necessárias
"""

from flask import Blueprint

necessidade_compra_bp = Blueprint('necessidade_compra', __name__, url_prefix='/necessidade-compra')

from . import routes
