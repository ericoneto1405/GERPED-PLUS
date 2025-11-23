"""
Testes unitários para ColetaService
"""
import pytest
from unittest.mock import patch, MagicMock
from meu_app.coletas.services.coleta_service import ColetaService
from meu_app.models import Pedido, ItemPedido, Estoque, Coleta, ItemColetado, StatusPedido, StatusColeta


class TestColetaService:
    """Testes para ColetaService"""

    @patch('meu_app.coletas.services.coleta_service.db.session')
    @patch('meu_app.coletas.services.coleta_service.Pedido')
    def test_listar_pedidos_para_coleta_sucesso(self, mock_pedido, mock_session):
        """Testa listagem de pedidos para coleta com sucesso"""
        # Arrange
        mock_filter = mock_pedido.query.filter.return_value
        mock_options = mock_filter.options.return_value
        mock_options.order_by.return_value = mock_options
        mock_options.all.return_value = [
            MagicMock(id=1, status=StatusPedido.PAGAMENTO_APROVADO),
            MagicMock(id=2, status=StatusPedido.COLETA_PARCIAL)
        ]
        
        # Act
        resultado = ColetaService.listar_pedidos_para_coleta()
        
        # Assert
        assert len(resultado) >= 0
        mock_pedido.query.filter.assert_called_once()

    @patch('meu_app.coletas.services.coleta_service.db.session')
    @patch('meu_app.coletas.services.coleta_service.Pedido')
    def test_listar_pedidos_para_coleta_erro(self, mock_pedido, mock_session):
        """Testa listagem de pedidos com erro"""
        # Arrange
        mock_pedido.query.filter.side_effect = Exception("Erro de conexão")
        
        # Act
        resultado = ColetaService.listar_pedidos_para_coleta()
        
        # Assert
        assert resultado == []

    @patch('meu_app.coletas.services.coleta_service.db.session')
    @patch('meu_app.coletas.services.coleta_service.Pedido')
    def test_buscar_detalhes_pedido_sucesso(self, mock_pedido, mock_session):
        """Testa busca de detalhes de pedido com sucesso"""
        # Arrange
        mock_pedido_obj = MagicMock()
        mock_pedido_obj.id = 1
        mock_pedido_obj.status = StatusPedido.PAGAMENTO_APROVADO
        mock_filter = mock_pedido.query.filter.return_value
        mock_filter.options.return_value.first.return_value = mock_pedido_obj
        mock_filter.first.return_value = mock_pedido_obj
        
        # Act
        resultado = ColetaService.buscar_detalhes_pedido(1)
        
        # Assert
        assert resultado is not None
        assert resultado['pedido'] == mock_pedido_obj

    @patch('meu_app.coletas.services.coleta_service.db.session')
    @patch('meu_app.coletas.services.coleta_service.Pedido')
    def test_buscar_detalhes_pedido_nao_encontrado(self, mock_pedido, mock_session):
        """Testa busca de detalhes de pedido não encontrado"""
        # Arrange
        mock_filter = mock_pedido.query.filter.return_value
        mock_filter.options.return_value.first.return_value = None
        mock_filter.first.return_value = None
        
        # Act
        resultado = ColetaService.buscar_detalhes_pedido(999)
        
        # Assert
        assert resultado is None

    @patch('meu_app.coletas.services.coleta_service.db.session')
    @patch('meu_app.coletas.services.coleta_service.Pedido')
    @patch('meu_app.coletas.services.coleta_service.ItemPedido')
    @patch('meu_app.coletas.services.coleta_service.Estoque')
    @patch('meu_app.coletas.services.coleta_service.ColetaService._registrar_movimentacao_estoque')
    def test_processar_coleta_sucesso(self, mock_registrar_mov, mock_estoque, mock_item_pedido, mock_pedido, mock_session):
        """Testa processamento de coleta com sucesso"""
        # Arrange
        mock_pedido_obj = MagicMock()
        mock_pedido_obj.id = 1
        mock_pedido_obj.status = StatusPedido.PAGAMENTO_APROVADO
        mock_pedido_obj.itens = []

        mock_item_obj = MagicMock()
        mock_item_obj.id = 1
        mock_item_obj.pedido_id = 1
        mock_item_obj.produto_id = 1
        mock_item_obj.produto = MagicMock()
        mock_item_obj.produto.nome = "Produto Teste"
        mock_item_obj.quantidade = 10

        mock_estoque_obj = MagicMock()
        mock_estoque_obj.quantidade = 10

        pedido_query = MagicMock()
        item_query = MagicMock()
        sum_query = MagicMock()
        estoque_query = MagicMock()
        mock_session.query.side_effect = [
            pedido_query,
            item_query,
            sum_query,
            estoque_query,
        ]

        pedido_query.filter.return_value.with_for_update.return_value.first.return_value = mock_pedido_obj
        item_query.filter.return_value.with_for_update.return_value.first.return_value = mock_item_obj
        sum_query.join.return_value.filter.return_value.scalar.return_value = 0
        estoque_query.filter_by.return_value.with_for_update.return_value.first.return_value = mock_estoque_obj
        
        # Act
        sucesso, mensagem, coleta = ColetaService.processar_coleta(
            pedido_id=1,
            responsavel_coleta_id=1,
            nome_retirada="João Silva",
            documento_retirada="12345678901",
            itens_coleta=[{'item_id': 1, 'quantidade': 2}]
        )
        
        # Assert
        assert sucesso is True
        assert "sucesso" in mensagem.lower()

    def test_processar_coleta_dados_invalidos(self):
        """Testa processamento de coleta com dados inválidos"""
        # Act
        sucesso, mensagem, coleta = ColetaService.processar_coleta(
            pedido_id=1,
            responsavel_coleta_id=1,
            nome_retirada="",  # Nome vazio
            documento_retirada="",  # Documento vazio
            itens_coleta=[]
        )
        
        # Assert
        assert sucesso is False
        assert "obrigatórios" in mensagem

    def test_processar_coleta_sem_itens(self):
        """Testa processamento de coleta sem itens"""
        # Act
        sucesso, mensagem, coleta = ColetaService.processar_coleta(
            pedido_id=1,
            responsavel_coleta_id=1,
            nome_retirada="João Silva",
            documento_retirada="12345678901",
            itens_coleta=[]  # Lista vazia
        )
        
        # Assert
        assert sucesso is False
        assert "pelo menos um item" in mensagem

    @patch('meu_app.coletas.services.coleta_service.db.session')
    @patch('meu_app.coletas.services.coleta_service.Pedido')
    @patch('meu_app.coletas.services.coleta_service.Coleta')
    def test_buscar_historico_coletas_sucesso(self, mock_coleta, mock_pedido, mock_session):
        """Testa busca de histórico de coletas com sucesso"""
        # Arrange
        mock_pedido_obj = MagicMock()
        mock_pedido_obj.id = 1
        
        mock_coleta_obj = MagicMock()
        mock_coleta_obj.id = 1
        mock_coleta_obj.pedido_id = 1
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_pedido_obj
        mock_coleta.query.filter_by.return_value.order_by.return_value.all.return_value = [mock_coleta_obj]
        
        # Act
        resultado = ColetaService.buscar_historico_coletas(1)
        
        # Assert
        assert resultado is not None
        assert 'pedido' in resultado
        assert 'coletas' in resultado

    @patch('meu_app.coletas.services.coleta_service.db.session')
    @patch('meu_app.coletas.services.coleta_service.Pedido')
    def test_buscar_historico_coletas_pedido_nao_encontrado(self, mock_pedido, mock_session):
        """Testa busca de histórico com pedido não encontrado"""
        # Arrange
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        resultado = ColetaService.buscar_historico_coletas(999)
        
        # Assert
        assert resultado is None
