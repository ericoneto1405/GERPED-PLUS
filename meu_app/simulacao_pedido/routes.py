"""Rotas do módulo Simulação de Pedido."""

from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, session
from sqlalchemy.orm import joinedload

from meu_app.decorators import login_obrigatorio, permissao_necessaria
from meu_app.models import (
    Apuracao,
    ItemPedido,
    Pedido,
    Produto,
)

simulacao_pedido_bp = Blueprint(
    "simulacao_pedido",
    __name__,
    url_prefix="/simulacao-pedido",
)


@simulacao_pedido_bp.route("/", methods=["GET"])
@login_obrigatorio
@permissao_necessaria("acesso_pedidos")
def index():
    """Tela inicial do módulo de Simulação de Pedido."""
    current_app.logger.info(
        "Simulação de Pedido acessada por %s",
        session.get("usuario_nome", "desconhecido"),
    )
    return render_template("simulacao_pedido/index.html")


@simulacao_pedido_bp.route("/dados", methods=["GET"])
@login_obrigatorio
@permissao_necessaria("acesso_pedidos")
def dados_simulacao():
    """
    Fornece dados consolidados para a simulação:
    - Produtos com custo e categoria
    - Verbas previstas (apuracao do período)
    - Desempenho atual (receita/custo) de pedidos liberados no mês
    """
    try:
        hoje = datetime.now()
        mes = hoje.month
        ano = hoje.year

        apuracao = (
            Apuracao.query.filter_by(mes=mes, ano=ano)
            .order_by(Apuracao.id.desc())
            .first()
        )
        if not apuracao:
            apuracao = (
                Apuracao.query.order_by(Apuracao.ano.desc(), Apuracao.mes.desc()).first()
            )

        verbas = {
            "total": float(apuracao.total_verbas) if apuracao else 0.0,
            "scann": float(apuracao.verba_scann) if apuracao else 0.0,
            "plano_negocios": float(apuracao.verba_plano_negocios) if apuracao else 0.0,
            "time_ambev": float(apuracao.verba_time_ambev) if apuracao else 0.0,
            "outras": float(apuracao.verba_outras_receitas) if apuracao else 0.0,
            "apuracao_id": apuracao.id if apuracao else None,
            "mes": apuracao.mes if apuracao else mes,
            "ano": apuracao.ano if apuracao else ano,
        }

        # Desempenho geral do período (liberados pelo comercial)
        inicio_mes = datetime(verbas["ano"], verbas["mes"], 1)
        if verbas["mes"] == 12:
            proximo_mes = datetime(verbas["ano"] + 1, 1, 1)
        else:
            proximo_mes = datetime(verbas["ano"], verbas["mes"] + 1, 1)

        pedidos = (
            Pedido.query.options(
                joinedload(Pedido.itens).joinedload(ItemPedido.produto)
            )
            .filter(
                Pedido.data >= inicio_mes,
                Pedido.data < proximo_mes,
                Pedido.confirmado_comercial == True,  # noqa: E712
            )
            .all()
        )

        total_receita = 0.0
        total_cpv = 0.0
        categorias_map = {}
        for pedido in pedidos:
            for item in pedido.itens:
                produto = item.produto
                cat = (produto.categoria or "OUTROS").upper() if produto else "OUTROS"
                receita = float(item.valor_total_venda or 0)
                preco_medio = float(produto.preco_medio_compra or 0) if produto else 0
                custo = float(item.quantidade or 0) * preco_medio
                total_receita += receita
                total_cpv += custo
                cat_data = categorias_map.setdefault(
                    cat, {"categoria": cat, "receita": 0.0, "custo": 0.0}
                )
                cat_data["receita"] += receita
                cat_data["custo"] += custo

        desempenho_geral = {
            "receita": total_receita,
            "cpv": total_cpv,
            "margem": total_receita - total_cpv,
            "pedidos_processados": len(pedidos),
        }

        categorias = []
        for cat, data in categorias_map.items():
            margem = data["receita"] - data["custo"]
            categorias.append(
                {
                    "categoria": cat,
                    "receita": round(data["receita"], 2),
                    "custo": round(data["custo"], 2),
                    "margem": round(margem, 2),
                }
            )

        # Produtos
        produtos = [
            {
                "id": p.id,
                "nome": p.nome,
                "categoria": (p.categoria or "OUTROS").upper(),
                "custo": float(p.preco_medio_compra or 0),
                "codigo": p.codigo_interno,
                "preco_atualizado_em": p.preco_atualizado_em.isoformat()
                if getattr(p, "preco_atualizado_em", None)
                else None,
            }
            for p in Produto.query.all()
        ]

        resposta = {
            "success": True,
            "mes": verbas["mes"],
            "ano": verbas["ano"],
            "verbas": verbas,
            "desempenho": {"geral": desempenho_geral, "categorias": categorias},
            "produtos": produtos,
        }
        return jsonify(resposta)
    except Exception as e:
        current_app.logger.error(f"Erro ao montar dados da simulação: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500
