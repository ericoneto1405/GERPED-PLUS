from __future__ import annotations
from datetime import datetime, timedelta
from calendar import monthrange
from typing import Dict, Any

from flask import current_app, session
from sqlalchemy import func

from . import db
from .models import Cliente, Produto, Pedido, ItemPedido, Pagamento, Apuracao, StatusPedido
from .pedidos.services import PedidoService


class DashboardService:
    """Responsável por montar o contexto exibido no painel principal."""

    def __init__(self):
        self.session = db.session

    def gerar_contexto(self, mes: int, ano: int) -> Dict[str, Any]:
        data_inicio, proximo_mes = self._intervalo_mes(mes, ano)

        total_pedidos = Pedido.query.filter(
            Pedido.data >= data_inicio,
            Pedido.data < proximo_mes
        ).count()

        pagamentos_periodo = self._buscar_pagamentos_periodo(data_inicio, proximo_mes)
        pagamentos_por_pedido = self._agrupar_pagamentos_por_pedido(pagamentos_periodo)

        pedido_totais, pedido_ratios = self._buscar_totais_por_pedido(list(pagamentos_por_pedido.keys()))
        faturamento_total = sum(pagamentos_por_pedido.values())
        pedidos_pagos = len(pagamentos_por_pedido)
        cpv_total = self._calcular_cpv_periodo(pagamentos_periodo, pedido_ratios)

        apuracao = Apuracao.query.filter_by(mes=mes, ano=ano).first()
        tem_apuracao = apuracao is not None
        total_verbas = self._calcular_verbas(apuracao) if tem_apuracao else 0.0

        margem_manobra = (faturamento_total - cpv_total) + total_verbas
        percentual_margem = (margem_manobra / faturamento_total * 100) if faturamento_total else 0

        total_clientes = Cliente.query.count()
        total_produtos = Produto.query.count()

        pedidos_recentes = (
            Pedido.query.options(
                db.joinedload(Pedido.cliente),
                db.joinedload(Pedido.itens)
            ).order_by(Pedido.data.desc()).limit(5).all()
        )

        dados_evolucao = self._montar_evolucao_diaria(mes, ano, pagamentos_periodo, pedido_ratios, total_verbas, tem_apuracao)

        liberados = self._consultar_pedidos_liberados(data_inicio, proximo_mes)
        faturamento_liberados = float(liberados.total_venda or 0)
        cpv_liberados = float(liberados.total_compra or 0)
        pedidos_liberados = int(liberados.qtd_pedidos or 0)
        margem_liberados = (faturamento_liberados + total_verbas) - cpv_liberados
        percentual_margem_liberados = (margem_liberados / faturamento_liberados * 100) if faturamento_liberados else 0

        faturamento_projetado_mes, margem_projetada_mes, percentual_margem_projetada = self._projetar_resultado_mensal(
            mes, ano, faturamento_total, cpv_total, total_verbas
        )

        necessidade_compra = PedidoService.calcular_necessidade_compra()

        current_app.logger.info(
            "Painel acessado por usuário %s", session.get('usuario_nome', 'N/A')
        )

        return {
            'total_pedidos': total_pedidos,
            'pedidos_pagos': pedidos_pagos,
            'faturamento_total': faturamento_total,
            'cpv_total': cpv_total,
            'tem_apuracao': tem_apuracao,
            'total_verbas': total_verbas,
            'margem_manobra': margem_manobra,
            'percentual_margem': percentual_margem,
            'total_valor': faturamento_total,
            'total_clientes': total_clientes,
            'total_produtos': total_produtos,
            'pedidos_recentes': pedidos_recentes,
            'dados_evolucao': dados_evolucao,
            'faturamento_liberados': faturamento_liberados,
            'cpv_liberados': cpv_liberados,
            'margem_liberados': margem_liberados,
            'percentual_margem_liberados': percentual_margem_liberados,
            'pedidos_liberados': pedidos_liberados,
            'faturamento_projetado_mes': faturamento_projetado_mes,
            'margem_projetada_mes': margem_projetada_mes,
            'percentual_margem_projetada': percentual_margem_projetada,
            'necessidade_compra': necessidade_compra,
            'mes': mes,
            'ano': ano,
        }

    def _buscar_pagamentos_periodo(self, inicio: datetime, fim: datetime):
        pagamentos_raw = (
            self.session.query(
                Pagamento.pedido_id,
                Pagamento.valor,
                Pagamento.data_pagamento
            )
            .join(Pedido, Pagamento.pedido_id == Pedido.id)
            .filter(
                Pagamento.data_pagamento >= inicio,
                Pagamento.data_pagamento < fim,
                Pedido.status == StatusPedido.PAGAMENTO_APROVADO
            )
            .all()
        )
        return [
            {
                'pedido_id': pg.pedido_id,
                'valor': float(pg.valor or 0),
                'data': pg.data_pagamento or inicio,
            }
            for pg in pagamentos_raw
        ]

    @staticmethod
    def _agrupar_pagamentos_por_pedido(pagamentos):
        resultado = {}
        for pagamento in pagamentos:
            resultado[pagamento['pedido_id']] = resultado.get(pagamento['pedido_id'], 0.0) + pagamento['valor']
        return resultado

    def _buscar_totais_por_pedido(self, pedido_ids):
        if not pedido_ids:
            return {}, {}
        linhas = (
            self.session.query(
                ItemPedido.pedido_id.label('pedido_id'),
                func.coalesce(func.sum(ItemPedido.valor_total_venda), 0).label('total_venda'),
                func.coalesce(
                    func.sum(ItemPedido.quantidade * func.coalesce(Produto.preco_medio_compra, 0)),
                    0,
                ).label('total_compra'),
            )
            .outerjoin(Produto, Produto.id == ItemPedido.produto_id)
            .filter(ItemPedido.pedido_id.in_(pedido_ids))
            .group_by(ItemPedido.pedido_id)
            .all()
        )
        totais = {}
        ratios = {}
        for linha in linhas:
            total_venda = float(linha.total_venda or 0)
            total_compra = float(linha.total_compra or 0)
            totais[linha.pedido_id] = {
                'total_venda': total_venda,
                'total_compra': total_compra,
            }
            ratios[linha.pedido_id] = (total_compra / total_venda) if total_venda > 0 else 0.0
        return totais, ratios

    @staticmethod
    def _calcular_cpv_periodo(pagamentos, pedido_ratios):
        return sum(
            pagamento['valor'] * pedido_ratios.get(pagamento['pedido_id'], 0.0)
            for pagamento in pagamentos
        )

    @staticmethod
    def _calcular_verbas(apuracao: Apuracao) -> float:
        return float(
            (apuracao.verba_scann or 0)
            + (apuracao.verba_plano_negocios or 0)
            + (apuracao.verba_time_ambev or 0)
            + (apuracao.verba_outras_receitas or 0)
        )

    def _montar_evolucao_diaria(self, mes, ano, pagamentos, pedido_ratios, total_verbas, tem_apuracao):
        dados = {'labels': [], 'receita_verbas': [], 'cpv_total': [], 'margem': []}
        pagamentos_por_dia = {}
        for pagamento in pagamentos:
            dia = pagamento['data'].date()
            entry = pagamentos_por_dia.setdefault(dia, {'receita': 0.0, 'cpv': 0.0})
            entry['receita'] += pagamento['valor']
            entry['cpv'] += pagamento['valor'] * pedido_ratios.get(pagamento['pedido_id'], 0.0)

        _, ultimo_dia = monthrange(ano, mes)
        verbas_diarias = (total_verbas / ultimo_dia) if (tem_apuracao and ultimo_dia > 0) else 0.0

        for dia in range(1, ultimo_dia + 1):
            data_dia = datetime(ano, mes, dia).date()
            receita_dia = pagamentos_por_dia.get(data_dia, {}).get('receita', 0.0)
            cpv_dia = pagamentos_por_dia.get(data_dia, {}).get('cpv', 0.0)
            margem_dia = (receita_dia + verbas_diarias) - cpv_dia

            dados['labels'].append(f"{dia:02d}")
            dados['receita_verbas'].append(receita_dia + verbas_diarias)
            dados['cpv_total'].append(cpv_dia)
            dados['margem'].append(margem_dia)
        return dados

    def _consultar_pedidos_liberados(self, inicio, fim):
        return (
            self.session.query(
                func.coalesce(func.sum(ItemPedido.valor_total_venda), 0).label('total_venda'),
                func.coalesce(
                    func.sum(ItemPedido.quantidade * func.coalesce(Produto.preco_medio_compra, 0)),
                    0,
                ).label('total_compra'),
                func.count(func.distinct(Pedido.id)).label('qtd_pedidos')
            )
            .select_from(Pedido)
            .outerjoin(ItemPedido, ItemPedido.pedido_id == Pedido.id)
            .outerjoin(Produto, Produto.id == ItemPedido.produto_id)
            .filter(
                Pedido.data >= inicio,
                Pedido.data < fim,
                Pedido.confirmado_comercial == True  # noqa: E712
            )
            .one()
        )

    def _projetar_resultado_mensal(self, mes, ano, faturamento_total, cpv_total, total_verbas):
        _, ultimo_dia = monthrange(ano, mes)
        hoje = datetime.now()
        if ano == hoje.year and mes == hoje.month:
            dias_passados = max(min(hoje.day, ultimo_dia), 1)
        elif datetime(ano, mes, ultimo_dia) < hoje:
            dias_passados = ultimo_dia
        else:
            dias_passados = 1

        progresso = max(dias_passados / ultimo_dia, 0.01)
        faturamento_proj = faturamento_total / progresso if progresso else faturamento_total
        cpv_proj = cpv_total / progresso if progresso else cpv_total
        margem_proj = (faturamento_proj + total_verbas) - cpv_proj
        perc_margem_proj = (margem_proj / faturamento_proj * 100) if faturamento_proj else 0
        return faturamento_proj, margem_proj, perc_margem_proj

    @staticmethod
    def _intervalo_mes(mes: int, ano: int):
        inicio = datetime(ano, mes, 1)
        if mes == 12:
            proximo = datetime(ano + 1, 1, 1)
        else:
            proximo = datetime(ano, mes + 1, 1)
        return inicio, proximo

    @staticmethod
    def contexto_vazio(mes: int, ano: int) -> Dict[str, Any]:
        return {
            'total_pedidos': 0,
            'pedidos_pagos': 0,
            'faturamento_total': 0.0,
            'cpv_total': 0.0,
            'tem_apuracao': False,
            'total_verbas': 0.0,
            'margem_manobra': 0.0,
            'percentual_margem': 0.0,
            'total_valor': 0,
            'total_clientes': 0,
            'total_produtos': 0,
            'pedidos_recentes': [],
            'dados_evolucao': {'labels': [], 'receita_verbas': [], 'cpv_total': [], 'margem': []},
            'faturamento_liberados': 0.0,
            'cpv_liberados': 0.0,
            'margem_liberados': 0.0,
            'percentual_margem_liberados': 0.0,
            'pedidos_liberados': 0,
            'faturamento_projetado_mes': 0.0,
            'margem_projetada_mes': 0.0,
            'percentual_margem_projetada': 0.0,
            'necessidade_compra': [],
            'mes': mes,
            'ano': ano,
        }
