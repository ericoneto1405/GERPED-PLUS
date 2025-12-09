"""Camada de serviços da Análise de Compra."""

from typing import Dict, List

from flask import current_app
from sqlalchemy import and_, func

from meu_app.models import (
    Cliente,
    Estoque,
    ItemColetado,
    ItemPedido,
    Pedido,
    Produto,
    StatusPedido,
    db,
)


class NecessidadeCompraService:
    """Fornece os dados estruturados para o dashboard de Análise de Compra."""

    STATUS_RELEVANTES = (
        StatusPedido.PAGAMENTO_APROVADO,
        StatusPedido.COLETA_PARCIAL,
        StatusPedido.COLETA_CONCLUIDA,
    )

    @classmethod
    def obter_contexto_dashboard(cls) -> Dict[str, List[Dict]]:
        """Retorna o contexto completo utilizado no template da análise."""
        try:
            clientes = cls._agrupar_por_cliente()
            produtos = cls._resumir_por_produto()
            total_necessidade = sum(max(item["comprar"], 0) for item in produtos)

            return {
                "clientes": clientes,
                "produtos": produtos,
                "total_necessidade": total_necessidade,
            }
        except Exception as exc:  # pragma: no cover - erro logado e fallback
            current_app.logger.error(
                "Erro ao calcular contexto da análise de compra: %s", exc
            )
            return {"clientes": [], "produtos": [], "total_necessidade": 0}

    @classmethod
    def _agrupar_por_cliente(cls) -> List[Dict]:
        """Agrupa pedidos por cliente trazendo pedido/coleta/falta."""
        itens_por_cliente = (
            db.session.query(
                Cliente.id.label("cliente_id"),
                Cliente.nome.label("cliente_nome"),
                Pedido.id.label("pedido_id"),
                Produto.id.label("produto_id"),
                Produto.nome.label("produto_nome"),
                func.sum(ItemPedido.quantidade).label("quantidade"),
            )
            .join(Pedido, Pedido.cliente_id == Cliente.id)
            .join(ItemPedido, ItemPedido.pedido_id == Pedido.id)
            .join(Produto, Produto.id == ItemPedido.produto_id)
            .filter(Pedido.status.in_(cls.STATUS_RELEVANTES))
            .group_by(
                Cliente.id,
                Cliente.nome,
                Pedido.id,
                Produto.id,
                Produto.nome,
            )
        ).subquery()

        itens_coletados = (
            db.session.query(
                ItemPedido.pedido_id.label("pedido_id"),
                ItemPedido.produto_id.label("produto_id"),
                func.sum(ItemColetado.quantidade_coletada).label("coletado"),
            )
            .join(ItemColetado, ItemColetado.item_pedido_id == ItemPedido.id)
            .join(Pedido, Pedido.id == ItemPedido.pedido_id)
            .filter(Pedido.status.in_(cls.STATUS_RELEVANTES))
            .group_by(ItemPedido.pedido_id, ItemPedido.produto_id)
        ).subquery()

        linhas = (
            db.session.query(
                itens_por_cliente.c.cliente_id,
                itens_por_cliente.c.cliente_nome,
                itens_por_cliente.c.pedido_id,
                itens_por_cliente.c.produto_id,
                itens_por_cliente.c.produto_nome,
                itens_por_cliente.c.quantidade,
                func.coalesce(itens_coletados.c.coletado, 0).label("coletado"),
            )
            .outerjoin(
                itens_coletados,
                and_(
                    itens_coletados.c.pedido_id == itens_por_cliente.c.pedido_id,
                    itens_coletados.c.produto_id == itens_por_cliente.c.produto_id,
                ),
            )
            .order_by(
                itens_por_cliente.c.cliente_nome,
                itens_por_cliente.c.pedido_id,
                itens_por_cliente.c.produto_nome,
            )
            .all()
        )

        clientes_dict: Dict[int, Dict] = {}
        for row in linhas:
            cliente = clientes_dict.setdefault(
                row.cliente_id,
                {
                    "cliente_nome": row.cliente_nome,
                    "pedidos": set(),
                    "produtos": {},
                },
            )
            cliente["pedidos"].add(row.pedido_id)

            produto = cliente["produtos"].setdefault(
                row.produto_id,
                {
                    "produto_nome": row.produto_nome,
                    "quantidade": 0,
                    "coletado": 0,
                },
            )
            produto["quantidade"] += int(row.quantidade or 0)
            produto["coletado"] += int(row.coletado or 0)

        clientes_lista: List[Dict] = []
        for dados in clientes_dict.values():
            produtos = []
            for produto in dados["produtos"].values():
                falta = max(produto["quantidade"] - produto["coletado"], 0)
                produtos.append(
                    {
                        "produto_nome": produto["produto_nome"],
                        "quantidade": produto["quantidade"],
                        "coletado": produto["coletado"],
                        "falta_coletar": falta,
                    }
                )

            clientes_lista.append(
                {
                    "cliente_nome": dados["cliente_nome"],
                    "pedidos": sorted(dados["pedidos"]),
                    "produtos": sorted(produtos, key=lambda x: x["produto_nome"]),
                }
            )

        clientes_lista.sort(key=lambda x: x["cliente_nome"].lower())
        return clientes_lista

    @classmethod
    def _resumir_por_produto(cls) -> List[Dict]:
        """Gera a tabela consolidada de pedidos x estoque x comprar."""

        itens_produto = (
            db.session.query(
                ItemPedido.produto_id.label("produto_id"),
                func.sum(ItemPedido.quantidade).label("quantidade"),
            )
            .join(Pedido, Pedido.id == ItemPedido.pedido_id)
            .filter(Pedido.status.in_(cls.STATUS_RELEVANTES))
            .group_by(ItemPedido.produto_id)
        ).subquery()

        coletado_produto = (
            db.session.query(
                ItemPedido.produto_id.label("produto_id"),
                func.sum(ItemColetado.quantidade_coletada).label("coletado"),
            )
            .join(ItemColetado, ItemColetado.item_pedido_id == ItemPedido.id)
            .join(Pedido, Pedido.id == ItemPedido.pedido_id)
            .filter(Pedido.status.in_(cls.STATUS_RELEVANTES))
            .group_by(ItemPedido.produto_id)
        ).subquery()

        linhas = (
            db.session.query(
                Produto.id.label("produto_id"),
                Produto.nome.label("produto_nome"),
                func.coalesce(itens_produto.c.quantidade, 0).label("pedidos"),
                func.coalesce(coletado_produto.c.coletado, 0).label("coletado"),
                func.coalesce(func.max(Estoque.quantidade), 0).label("estoque"),
            )
            .join(itens_produto, itens_produto.c.produto_id == Produto.id)
            .outerjoin(coletado_produto, coletado_produto.c.produto_id == Produto.id)
            .outerjoin(Estoque, Estoque.produto_id == Produto.id)
            .group_by(
                Produto.id,
                Produto.nome,
                itens_produto.c.quantidade,
                coletado_produto.c.coletado,
            )
            .all()
        )

        produtos = []
        for row in linhas:
            pedidos = int(row.pedidos or 0)
            estoque = int(row.estoque or 0)
            coletado = int(row.coletado or 0)
            comprar = pedidos - estoque - coletado

            produtos.append(
                {
                    "produto_nome": row.produto_nome,
                    "pedidos": pedidos,
                    "estoque": estoque,
                    "comprado": coletado,
                    "comprar": comprar,
                }
            )

        produtos.sort(key=lambda x: x["comprar"], reverse=True)
        return produtos
