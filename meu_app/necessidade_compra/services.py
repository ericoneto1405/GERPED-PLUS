"""
Services para o módulo de Necessidade de Compra
Funcionalidade original do Dashboard - Análise simples baseada em pedidos liberados
"""

from typing import List, Dict
from flask import current_app
from sqlalchemy import func
from meu_app.models import (
    db, Produto, ItemPedido, Pedido, Estoque, StatusPedido
)


class NecessidadeCompraService:
    """Serviço para análise de necessidade de compra - versão original simples"""
    
    @staticmethod
    def calcular_necessidade_compra() -> List[Dict]:
        """
        Calcula a necessidade de compra baseada nos pedidos pagos e em coleta
        (Lógica original do Dashboard)
        
        Returns:
            List[Dict]: Lista com produtos e necessidade de compra
        """
        try:
            pedidos_liberados = (
                db.session.query(
                    Produto.id.label('produto_id'),
                    Produto.nome.label('produto_nome'),
                    func.sum(ItemPedido.quantidade).label('quantidade_pedida'),
                    func.sum(ItemPedido.valor_total_compra).label('valor_total_compra'),
                )
                .join(ItemPedido, ItemPedido.produto_id == Produto.id)
                .join(Pedido, Pedido.id == ItemPedido.pedido_id)
                .filter(
                    Pedido.status.in_([
                        StatusPedido.PAGAMENTO_APROVADO,
                        StatusPedido.COLETA_PARCIAL,
                        StatusPedido.COLETA_CONCLUIDA
                    ])
                )
                .group_by(Produto.id, Produto.nome)
                .all()
            )

            resultado: List[Dict] = []

            for row in pedidos_liberados:
                quantidade_pedida = int(row.quantidade_pedida or 0)
                if quantidade_pedida <= 0:
                    continue

                estoque = Estoque.query.filter_by(produto_id=row.produto_id).first()
                quantidade_estoque = estoque.quantidade if estoque else 0

                saldo = quantidade_estoque - quantidade_pedida
                necessidade_compra = abs(saldo) if saldo < 0 else 0

                valor_total_compra = float(row.valor_total_compra or 0)
                valor_compra_unitario = (
                    valor_total_compra / quantidade_pedida if quantidade_pedida > 0 else 0.0
                )
                valor_total_necessidade = necessidade_compra * valor_compra_unitario

                resultado.append({
                    'produto_id': row.produto_id,
                    'produto_nome': row.produto_nome,
                    'quantidade_pedida': quantidade_pedida,
                    'quantidade_estoque': quantidade_estoque,
                    'saldo': saldo,
                    'necessidade_compra': necessidade_compra,
                    'valor_compra': valor_compra_unitario,
                    'valor_total_necessidade': valor_total_necessidade,
                    'status': 'CRÍTICO' if saldo < 0 else 'SUFICIENTE' if saldo > 0 else 'ZERADO'
                })

            resultado.sort(key=lambda x: (x['necessidade_compra'], x['produto_nome']), reverse=True)

            return resultado
            
        except Exception as e:
            current_app.logger.error(f"Erro ao calcular necessidade de compra: {str(e)}")
            return []
