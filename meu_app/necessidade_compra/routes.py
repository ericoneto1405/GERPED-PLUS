"""
Routes para o módulo de Necessidade de Compra
Funcionalidade original do Dashboard - Análise simples
"""

from flask import current_app, render_template
from ..decorators import login_obrigatorio
from . import necessidade_compra_bp
from .services import NecessidadeCompraService


@necessidade_compra_bp.route('/')
@login_obrigatorio
def dashboard():
    """Página principal de análise de necessidade de compra - versão original"""
    try:
        contexto = NecessidadeCompraService.obter_contexto_dashboard()
        return render_template(
            'necessidade_compra/dashboard.html',
            clientes_pedidos=contexto['clientes'],
            produtos_resumo=contexto['produtos'],
            total_necessidade=contexto['total_necessidade'],
        )
    except Exception as e:  # pragma: no cover - log e fallback visual
        current_app.logger.error(f"Erro ao carregar análise de compra: {str(e)}")
        return render_template(
            'necessidade_compra/dashboard.html',
            clientes_pedidos=[],
            produtos_resumo=[],
            total_necessidade=0,
        )
