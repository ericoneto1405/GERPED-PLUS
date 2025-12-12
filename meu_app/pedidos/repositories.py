"""
Repository para o módulo de pedidos.

Implementa o padrão Repository para acesso a dados de pedidos.
"""

from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from ..models import db, Pedido, ItemPedido, Pagamento, PagamentoAnexo, StatusPedido


class PedidoRepository:
    """Repository para operações de banco de dados de pedidos."""
    
    def __init__(self):
        """Inicializa o repositório"""
        self.db = db
    
    def buscar_por_id(self, pedido_id: int) -> Optional[Pedido]:
        """Busca pedido por ID com relacionamentos."""
        try:
            return Pedido.query.get(pedido_id)
        except SQLAlchemyError as e:
            print(f"Erro ao buscar pedido por ID {pedido_id}: {str(e)}")
            return None
    
    def listar_todos(self) -> List[Pedido]:
        """Lista todos os pedidos."""
        try:
            return Pedido.query.order_by(Pedido.data.desc()).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar pedidos: {str(e)}")
            return []
    
    def listar_por_cliente(self, cliente_id: int) -> List[Pedido]:
        """Lista pedidos de um cliente."""
        try:
            return Pedido.query.filter_by(cliente_id=cliente_id)\
                .order_by(Pedido.data.desc()).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar pedidos do cliente {cliente_id}: {str(e)}")
            return []
    
    def listar_por_status(self, status: StatusPedido) -> List[Pedido]:
        """Lista pedidos por status."""
        try:
            return Pedido.query.filter_by(status=status)\
                .order_by(Pedido.data.desc()).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar pedidos por status {status}: {str(e)}")
            return []
    
    def listar_por_periodo(self, data_inicio: datetime, data_fim: datetime) -> List[Pedido]:
        """Lista pedidos em um período."""
        try:
            return Pedido.query.filter(
                Pedido.data >= data_inicio,
                Pedido.data <= data_fim
            ).order_by(Pedido.data.desc()).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar pedidos por período: {str(e)}")
            return []
    
    def criar(self, pedido: Pedido) -> Pedido:
        """Cria novo pedido."""
        try:
            self.db.session.add(pedido)
            self.db.session.commit()
            return pedido
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao criar pedido: {str(e)}")
            raise
    
    def atualizar(self, pedido: Pedido) -> Pedido:
        """Atualiza pedido existente."""
        try:
            self.db.session.commit()
            return pedido
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao atualizar pedido: {str(e)}")
            raise
    
    def excluir(self, pedido: Pedido) -> bool:
        """Exclui pedido do banco de dados."""
        try:
            self.db.session.delete(pedido)
            self.db.session.commit()
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao excluir pedido: {str(e)}")
            raise


class ItemPedidoRepository:
    """Repository para itens de pedido."""
    
    def __init__(self):
        """Inicializa o repositório"""
        self.db = db
    
    def buscar_por_id(self, item_id: int) -> Optional[ItemPedido]:
        """Busca item de pedido por ID."""
        try:
            return ItemPedido.query.get(item_id)
        except SQLAlchemyError as e:
            print(f"Erro ao buscar item por ID {item_id}: {str(e)}")
            return None
    
    def listar_por_pedido(self, pedido_id: int) -> List[ItemPedido]:
        """Lista itens de um pedido."""
        try:
            return ItemPedido.query.filter_by(pedido_id=pedido_id).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar itens do pedido {pedido_id}: {str(e)}")
            return []
    
    def criar(self, item: ItemPedido) -> ItemPedido:
        """Cria novo item de pedido."""
        try:
            self.db.session.add(item)
            self.db.session.commit()
            return item
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao criar item de pedido: {str(e)}")
            raise
    
    def excluir(self, item: ItemPedido) -> bool:
        """Exclui item de pedido."""
        try:
            self.db.session.delete(item)
            self.db.session.commit()
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao excluir item de pedido: {str(e)}")
            raise


class PagamentoRepository:
    """Repository para pagamentos."""
    
    def __init__(self):
        """Inicializa o repositório"""
        self.db = db
    
    def buscar_por_id(self, pagamento_id: int) -> Optional[Pagamento]:
        """Busca pagamento por ID."""
        try:
            return Pagamento.query.get(pagamento_id)
        except SQLAlchemyError as e:
            print(f"Erro ao buscar pagamento por ID {pagamento_id}: {str(e)}")
            return None
    
    def buscar_por_sha256(self, sha256: str) -> Optional[Pagamento]:
        """Busca pagamento por hash SHA256 do recibo."""
        try:
            try:
                anexo = PagamentoAnexo.query.filter_by(sha256=sha256).first()
            except SQLAlchemyError:
                anexo = None
            if anexo:
                return anexo.pagamento
            return Pagamento.query.filter_by(recibo_sha256=sha256).first()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar pagamento por SHA256: {str(e)}")
            return None
    
    def listar_por_pedido(self, pedido_id: int) -> List[Pagamento]:
        """Lista pagamentos de um pedido."""
        try:
            return Pagamento.query.filter_by(pedido_id=pedido_id)\
                .order_by(Pagamento.data_pagamento.desc()).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar pagamentos do pedido {pedido_id}: {str(e)}")
            return []
    
    def criar(self, pagamento: Pagamento) -> Pagamento:
        """Cria novo pagamento."""
        try:
            self.db.session.add(pagamento)
            self.db.session.commit()
            return pagamento
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao criar pagamento: {str(e)}")
            raise
    
    def excluir(self, pagamento: Pagamento) -> bool:
        """Exclui pagamento."""
        try:
            self.db.session.delete(pagamento)
            self.db.session.commit()
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao excluir pagamento: {str(e)}")
            raise
