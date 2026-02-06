#!/usr/bin/env python3
"""
Estorna (reverte) todas as coletas:
- Reposição do estoque baseada nos itens coletados
- Atualiza status dos pedidos para PAGAMENTO_APROVADO
- Remove registros de Coleta e ItemColetado

Uso:
  python scripts/estornar_coletas.py           # modo simulação (dry-run)
  python scripts/estornar_coletas.py --aplicar # aplica alterações
"""
import argparse
from typing import List, Tuple

from sqlalchemy import func

from meu_app import create_app, db
from meu_app.models import (
    Coleta,
    ItemColetado,
    ItemPedido,
    Estoque,
    MovimentacaoEstoque,
    Pedido,
    StatusPedido,
)


def _buscar_resumo() -> Tuple[int, int, int, List[Tuple[int, int]]]:
    total_coletas = Coleta.query.count()
    total_itens = ItemColetado.query.count()
    total_pedidos = (
        db.session.query(func.count(func.distinct(Coleta.pedido_id))).scalar() or 0
    )
    ajustes = (
        db.session.query(
            ItemPedido.produto_id.label("produto_id"),
            func.coalesce(func.sum(ItemColetado.quantidade_coletada), 0).label("qtd"),
        )
        .join(ItemColetado, ItemColetado.item_pedido_id == ItemPedido.id)
        .join(Coleta, Coleta.id == ItemColetado.coleta_id)
        .group_by(ItemPedido.produto_id)
        .all()
    )
    ajustes = [(row.produto_id, int(row.qtd or 0)) for row in ajustes]
    return total_coletas, total_itens, total_pedidos, ajustes


def _imprimir_resumo(total_coletas, total_itens, total_pedidos, ajustes, limite=10):
    print("Resumo das coletas encontradas:")
    print(f"- Coletas: {total_coletas}")
    print(f"- Itens coletados: {total_itens}")
    print(f"- Pedidos afetados: {total_pedidos}")
    print(f"- Produtos com ajuste de estoque: {len(ajustes)}")
    if ajustes:
        print("Exemplos de ajuste de estoque (produto_id -> qtd a devolver):")
        for produto_id, qtd in ajustes[:limite]:
            print(f"  - {produto_id} -> {qtd}")
        if len(ajustes) > limite:
            print(f"  ... (+{len(ajustes) - limite} produtos)")


def main():
    parser = argparse.ArgumentParser(description="Estornar todas as coletas.")
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Aplica as alterações no banco (sem este flag é apenas simulação).",
    )
    parser.add_argument(
        "--responsavel",
        default="Sistema (estorno coletas)",
        help="Nome do responsável para registrar na movimentação de estoque.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        total_coletas, total_itens, total_pedidos, ajustes = _buscar_resumo()
        _imprimir_resumo(total_coletas, total_itens, total_pedidos, ajustes)

        if total_coletas == 0:
            print("\nNenhuma coleta para estornar.")
            return

        if not args.aplicar:
            print("\nModo simulação: nenhuma alteração foi aplicada.")
            print("Para aplicar, execute com --aplicar.")
            return

        try:
            # Ajuste de estoque (entrada)
            for produto_id, qtd in ajustes:
                if qtd <= 0:
                    continue
                estoque = (
                    db.session.query(Estoque)
                    .filter_by(produto_id=produto_id)
                    .with_for_update()
                    .first()
                )
                if not estoque:
                    raise RuntimeError(
                        f"Estoque não encontrado para produto_id={produto_id}"
                    )
                quantidade_anterior = estoque.quantidade
                quantidade_atual = quantidade_anterior + qtd

                movimentacao = MovimentacaoEstoque(
                    produto_id=produto_id,
                    tipo_movimentacao="Entrada",
                    quantidade_anterior=quantidade_anterior,
                    quantidade_movimentada=qtd,
                    quantidade_atual=quantidade_atual,
                    motivo="Estorno de coletas (testes)",
                    responsavel=args.responsavel,
                    observacoes="Reposição automática por estorno total de coletas",
                )
                db.session.add(movimentacao)
                estoque.quantidade = quantidade_atual

            # Reverter status dos pedidos afetados
            pedido_ids = [
                row[0]
                for row in db.session.query(Coleta.pedido_id).distinct().all()
                if row and row[0] is not None
            ]
            if pedido_ids:
                db.session.query(Pedido).filter(
                    Pedido.id.in_(pedido_ids),
                    Pedido.status.in_(
                        [StatusPedido.COLETA_PARCIAL, StatusPedido.COLETA_CONCLUIDA]
                    ),
                ).update(
                    {Pedido.status: StatusPedido.PAGAMENTO_APROVADO},
                    synchronize_session=False,
                )

            # Remover itens coletados e coletas
            db.session.query(ItemColetado).delete(synchronize_session=False)
            db.session.query(Coleta).delete(synchronize_session=False)

            db.session.commit()
            print("\nEstorno aplicado com sucesso.")
        except Exception as exc:
            db.session.rollback()
            print(f"\nErro ao aplicar estorno: {exc}")
            raise


if __name__ == "__main__":
    main()
