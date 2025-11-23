from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from meu_app.models import StatusPedido
from meu_app.pedidos.services import PedidoService


def _build_pedido(pedido_id: int, status: StatusPedido, data: datetime) -> SimpleNamespace:
    """Cria um pedido simples para ser usado nos testes de listagem."""
    return SimpleNamespace(
        id=pedido_id,
        status=status,
        confirmado_comercial=True,
        data=data,
        cliente=SimpleNamespace(nome=f"Cliente {pedido_id}"),
        itens=[SimpleNamespace(valor_total_venda=100.0)],
        pagamentos=[SimpleNamespace(valor=100.0)]
    )


def _configure_query(mock_pedido_model, mock_db, pedidos):
    """Configura os mocks da query para retornar os pedidos informados."""
    mock_query = Mock()
    mock_pedido_model.query.order_by.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.options.return_value = mock_query
    mock_query.all.return_value = pedidos
    mock_db.joinedload.side_effect = lambda *args, **kwargs: Mock()


class TestPedidoServiceListagem:
    @patch('meu_app.pedidos.services.db')
    @patch('meu_app.pedidos.services.Pedido')
    def test_listar_pedidos_inclui_coletados_concluidos(self, mock_pedido_model, mock_db):
        """Pedidos totalmente coletados devem continuar aparecendo no filtro."""
        pedido_parcial = _build_pedido(
            pedido_id=1,
            status=StatusPedido.COLETA_PARCIAL,
            data=datetime(2024, 1, 5, 12, 0)
        )
        pedido_concluido = _build_pedido(
            pedido_id=2,
            status=StatusPedido.COLETA_CONCLUIDA,
            data=datetime(2024, 1, 6, 9, 0)
        )

        _configure_query(mock_pedido_model, mock_db, [pedido_parcial, pedido_concluido])

        resultado = PedidoService.listar_pedidos(filtro_status='coletado_parcial')

        ids_retornados = {item['id_pedido'] for item in resultado}
        assert ids_retornados == {1, 2}

        concluido = next(item for item in resultado if item['id_pedido'] == 2)
        assert concluido['status_codigo'] == 'coleta_concluida'
        assert concluido['status'] == 'COLETA CONCLUÍDA'

    @patch('meu_app.pedidos.services.db')
    @patch('meu_app.pedidos.services.Pedido')
    def test_listar_pedidos_ordena_por_data_desc(self, mock_pedido_model, mock_db):
        """O pedido com data mais recente deve aparecer primeiro."""
        pedido_antigo = _build_pedido(
            pedido_id=10,
            status=StatusPedido.PENDENTE,
            data=datetime(2024, 1, 1, 8, 0)
        )
        pedido_recente = _build_pedido(
            pedido_id=20,
            status=StatusPedido.PENDENTE,
            data=datetime(2024, 2, 1, 8, 0)
        )

        _configure_query(mock_pedido_model, mock_db, [pedido_antigo, pedido_recente])

        resultado = PedidoService.listar_pedidos(ordenar_por='data', direcao='desc')

        assert resultado[0]['id_pedido'] == 20
        assert resultado[1]['id_pedido'] == 10
