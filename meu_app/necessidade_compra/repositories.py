"""
Repository para o módulo de Necessidade de Compra
"""

from typing import List, Dict, Any
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from meu_app import db
from meu_app.models import Produto, Estoque, ItemPedido, Pedido, StatusPedido
from decimal import Decimal


class NecessidadeCompraRepository:
    """Repository para consultas de análise de compra"""
    
    def __init__(self):
        self.db = db
    
    def obter_dados_produtos(self) -> List[Dict[str, Any]]:
        """
        Obtém dados consolidados de produtos, estoque e pedidos pendentes
        
        Returns:
            List[Dict]: Lista com dados dos produtos
        """
        try:
            # Query para obter produtos com estoque e pedidos pendentes
            query = self.db.session.query(
                Produto.id,
                Produto.nome,
                Produto.preco_medio_compra,
                func.coalesce(Estoque.quantidade, 0).label('estoque_atual'),
                func.coalesce(
                    self.db.session.query(func.sum(ItemPedido.quantidade))
                    .join(Pedido)
                    .filter(
                        ItemPedido.produto_id == Produto.id,
                        Pedido.status.in_([
                            StatusPedido.PENDENTE.value,
                            StatusPedido.PAGAMENTO_APROVADO.value
                        ])
                    )
                    .correlate(Produto)
                    .scalar_subquery(),
                    0
                ).label('quantidade_pedidos_pendentes')
            ).outerjoin(Estoque, Produto.id == Estoque.produto_id)
            
            resultados = query.all()
            
            # Converter para lista de dicionários
            produtos = []
            for row in resultados:
                produtos.append({
                    'produto_id': row.id,
                    'produto_nome': row.nome,
                    'preco_medio_compra': float(row.preco_medio_compra or 0),
                    'estoque_atual': int(row.estoque_atual or 0),
                    'quantidade_pedidos_pendentes': int(row.quantidade_pedidos_pendentes or 0)
                })
            
            return produtos
            
        except SQLAlchemyError as e:
            print(f"Erro ao obter dados de produtos: {str(e)}")
            return []
    
    def obter_historico_vendas(self, produto_id: int, dias: int = 30) -> int:
        """
        Obtém a média de vendas de um produto nos últimos N dias
        
        Args:
            produto_id: ID do produto
            dias: Número de dias para análise
            
        Returns:
            int: Média de vendas por dia
        """
        try:
            from datetime import datetime, timedelta
            
            data_limite = datetime.now() - timedelta(days=dias)
            
            total_vendido = self.db.session.query(
                func.sum(ItemPedido.quantidade)
            ).join(Pedido).filter(
                ItemPedido.produto_id == produto_id,
                Pedido.data >= data_limite,
                Pedido.status != StatusPedido.CANCELADO.value
            ).scalar()
            
            if total_vendido:
                return int(total_vendido / dias)
            return 0
            
        except SQLAlchemyError as e:
            print(f"Erro ao obter histórico de vendas: {str(e)}")
            return 0
    
    def obter_produto_por_id(self, produto_id: int) -> Dict[str, Any]:
        """
        Obtém dados detalhados de um produto específico
        
        Args:
            produto_id: ID do produto
            
        Returns:
            Dict: Dados do produto
        """
        try:
            produto = Produto.query.get(produto_id)
            if not produto:
                return {}
            
            estoque = Estoque.query.filter_by(produto_id=produto_id).first()
            
            # Pedidos pendentes
            quantidade_pendente = self.db.session.query(
                func.sum(ItemPedido.quantidade)
            ).join(Pedido).filter(
                ItemPedido.produto_id == produto_id,
                Pedido.status.in_([
                    StatusPedido.PENDENTE.value,
                    StatusPedido.PAGAMENTO_APROVADO.value
                ])
            ).scalar() or 0
            
            return {
                'produto_id': produto.id,
                'produto_nome': produto.nome,
                'preco_medio_compra': float(produto.preco_medio_compra or 0),
                'estoque_atual': estoque.quantidade if estoque else 0,
                'quantidade_pedidos_pendentes': int(quantidade_pendente)
            }
            
        except SQLAlchemyError as e:
            print(f"Erro ao obter produto: {str(e)}")
            return {}

