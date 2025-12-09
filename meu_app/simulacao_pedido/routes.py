"""Rotas do módulo Simulação de Pedido."""

from datetime import datetime
from calendar import monthrange

from flask import Blueprint, current_app, jsonify, render_template, session
from sqlalchemy.orm import joinedload

from meu_app.decorators import login_obrigatorio, permissao_necessaria
from meu_app.models import (
    Apuracao,
    ItemPedido,
    Pedido,
    Produto,
)
from meu_app.apuracao.services import ApuracaoService

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
    - Desempenho atual (receita/custo) por categoria no mês
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

        # Desempenho geral do período (pagos)
        dados_periodo = ApuracaoService.calcular_dados_periodo(
            verbas["mes"], verbas["ano"]
        )
        desempenho_geral = {
            "receita": float(dados_periodo.get("receita_calculada", 0.0)),
            "cpv": float(dados_periodo.get("cpv_calculado", 0.0)),
        }
        desempenho_geral["margem"] = desempenho_geral["receita"] - desempenho_geral["cpv"]
        desempenho_geral["pedidos_processados"] = int(
            dados_periodo.get("pedidos_periodo", 0)
        )

        # Desempenho por categoria (pedidos pagos no mês)
        inicio_mes = datetime(verbas["ano"], verbas["mes"], 1)
        fim_mes = datetime(
            verbas["ano"],
            verbas["mes"],
            monthrange(verbas["ano"], verbas["mes"])[1],
            23,
            59,
            59,
        )
        pedidos = (
            Pedido.query.options(
                joinedload(Pedido.itens).joinedload(ItemPedido.produto),
                joinedload(Pedido.pagamentos),
            )
            .filter(Pedido.data >= inicio_mes, Pedido.data <= fim_mes)
            .all()
        )

        categorias_map = {}
        for pedido in pedidos:
            total_pedido = sum(float(i.valor_total_venda) for i in pedido.itens)
            total_pago = sum(float(p.valor) for p in pedido.pagamentos)
            if total_pedido <= 0 or total_pago < total_pedido:
                continue  # segue lógica da apuração: só pagos e com valor

            for item in pedido.itens:
                cat = (item.produto.categoria or "OUTROS").upper()
                receita = float(item.valor_total_venda)
                custo = float(item.valor_total_compra)
                cat_data = categorias_map.setdefault(
                    cat, {"categoria": cat, "receita": 0.0, "custo": 0.0}
                )
                cat_data["receita"] += receita
                cat_data["custo"] += custo

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
