"""
Routes para o módulo de Necessidade de Compra
Funcionalidade original do Dashboard - Análise simples
"""

from flask import render_template
from ..decorators import login_obrigatorio
from . import necessidade_compra_bp
from .services import NecessidadeCompraService


@necessidade_compra_bp.route('/')
@login_obrigatorio
def dashboard():
    """Página principal de análise de necessidade de compra - versão original"""
    try:
        # Usar a mesma lógica do Dashboard original
        necessidade_compra = NecessidadeCompraService.calcular_necessidade_compra()
        
        return render_template('necessidade_compra/dashboard.html', 
                             necessidade_compra=necessidade_compra)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Erro ao carregar análise de compra: {str(e)}")
        return render_template('necessidade_compra/dashboard.html', 
                             necessidade_compra=[])
