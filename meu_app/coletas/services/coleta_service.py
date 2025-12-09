"""
Serviço unificado para operações de coleta - VERSÃO CONSOLIDADA
Implementa a sugestão CLI #2: Refatoração para unificar funcionalidades
"""
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from flask import current_app, has_app_context
from sqlalchemy import func, case, and_

from meu_app.models import (
    db,
    Pedido,
    Coleta,
    ItemColetado,
    ItemPedido,
    Pagamento,
    Usuario,
    Estoque,
    MovimentacaoEstoque,
    StatusColeta,
    StatusPedido,
)
from meu_app.exceptions import EstoqueError, ConfigurationError

logger = logging.getLogger(__name__)


def _app_logger():
    return current_app.logger if has_app_context() else logger


def _app_config_get(key: str, default=None):
    if has_app_context():
        return current_app.config.get(key, default)
    return default


def _app_debug() -> bool:
    if has_app_context():
        return bool(current_app.debug)
    return False


class ColetaService:
    """Serviço unificado para operações relacionadas à coleta"""

    STATUS_PEDIDOS_RELEVANTES = [
        StatusPedido.PAGAMENTO_APROVADO,
        StatusPedido.COLETA_PARCIAL,
        StatusPedido.COLETA_CONCLUIDA,
    ]
    
    @staticmethod
    def listar_pedidos_para_coleta(filtro: str = 'pendentes') -> List[Dict]:
        """
        Lista pedidos com filtro unificado (pendentes/coletados)
        
        Args:
            filtro: Filtro ('pendentes', 'coletados', 'todos')
        
        Returns:
            List[Dict]: Lista de pedidos com informações de coleta
        """
        try:
            itens_totais_sq = (
                db.session.query(
                    ItemPedido.pedido_id.label("pedido_id"),
                    func.sum(ItemPedido.quantidade).label("total_itens"),
                    func.sum(ItemPedido.valor_total_venda).label("total_venda"),
                )
                .group_by(ItemPedido.pedido_id)
                .subquery()
            )

            itens_coletados_sq = (
                db.session.query(
                    ItemPedido.pedido_id.label("pedido_id"),
                    func.sum(ItemColetado.quantidade_coletada).label("itens_coletados"),
                )
                .join(ItemColetado, ItemColetado.item_pedido_id == ItemPedido.id)
                .group_by(ItemPedido.pedido_id)
                .subquery()
            )

            pagamentos_sq = (
                db.session.query(
                    Pagamento.pedido_id.label("pedido_id"),
                    func.sum(Pagamento.valor).label("total_pago"),
                )
                .group_by(Pagamento.pedido_id)
                .subquery()
            )

            total_itens_col = func.coalesce(itens_totais_sq.c.total_itens, 0)
            itens_coletados_col = func.coalesce(itens_coletados_sq.c.itens_coletados, 0)
            total_venda_col = func.coalesce(itens_totais_sq.c.total_venda, 0)
            total_pago_col = func.coalesce(pagamentos_sq.c.total_pago, 0)

            coletado_completo_expr = case(
                (and_(total_itens_col > 0, itens_coletados_col >= total_itens_col), 1),
                else_=0,
            )
            pagamento_aprovado_expr = case(
                (and_(total_venda_col > 0, total_pago_col >= total_venda_col), 1),
                else_=0,
            )

            max_registros = _app_config_get("COLETAS_LISTA_MAX_REGISTROS", 200)

            pedidos_query = (
                db.session.query(
                    Pedido,
                    total_itens_col.label("total_itens"),
                    itens_coletados_col.label("itens_coletados"),
                    total_venda_col.label("total_venda"),
                    total_pago_col.label("total_pago"),
                    coletado_completo_expr.label("coletado_completo"),
                    pagamento_aprovado_expr.label("pagamento_aprovado"),
                )
                .outerjoin(itens_totais_sq, itens_totais_sq.c.pedido_id == Pedido.id)
                .outerjoin(itens_coletados_sq, itens_coletados_sq.c.pedido_id == Pedido.id)
                .outerjoin(pagamentos_sq, pagamentos_sq.c.pedido_id == Pedido.id)
                .filter(Pedido.status.in_(ColetaService.STATUS_PEDIDOS_RELEVANTES))
                .options(db.selectinload(Pedido.cliente))
                .order_by(Pedido.data.asc())
                .limit(max_registros)
            )

            # Executar query SEM filtros adicionais
            resultados = pedidos_query.all()

            if not resultados:
                return []

            _app_logger().debug(
                f"Filtro '{filtro}': {len(resultados)} pedidos retornados da query SQL"
            )

            # Aplicar filtro em Python (mais confiável que filtros SQL com expressões case)
            lista_pedidos: List[Dict] = []
            for (
                pedido,
                total_itens,
                itens_coletados,
                total_venda,
                total_pago,
                coletado_completo,
                pagamento_aprovado,
            ) in resultados:
                total_itens_int = int(total_itens or 0)
                itens_coletados_int = int(itens_coletados or 0)
                total_venda_float = float(total_venda or 0)
                total_pago_float = float(total_pago or 0)
                itens_pendentes = max(total_itens_int - itens_coletados_int, 0)
                
                # Calcular coletado_completo em Python (mais confiável)
                is_coletado_completo = (total_itens_int > 0 and itens_coletados_int >= total_itens_int)
                
                # Log detalhado em modo debug
                if _app_debug():
                    _app_logger().debug(
                        f"Pedido #{pedido.id}: total={total_itens_int}, "
                        f"coletados={itens_coletados_int}, "
                        f"completo={is_coletado_completo}, "
                        f"filtro={filtro}"
                    )
                
                # APLICAR FILTRO EM PYTHON
                if filtro == 'pendentes':
                    # Pular se não tem itens
                    if total_itens_int == 0:
                        _app_logger().debug(f"Pedido #{pedido.id} pulado: sem itens")
                        continue
                    # Pular se já está completamente coletado
                    if is_coletado_completo:
                        _app_logger().debug(f"Pedido #{pedido.id} pulado: já coletado")
                        continue
                elif filtro == 'coletados':
                    # Incluir apenas se está completamente coletado
                    if not is_coletado_completo:
                        continue
                # Se filtro == 'todos', não pular nenhum

                lista_pedidos.append(
                    {
                        "pedido": pedido,
                        "total_itens": total_itens_int,
                        "itens_coletados": itens_coletados_int,
                        "itens_pendentes": itens_pendentes,
                        "total_venda": total_venda_float,
                        "total_pago": total_pago_float,
                        "coletado_completo": is_coletado_completo,
                        "pagamento_aprovado": bool(pagamento_aprovado),
                    }
                )

            _app_logger().debug(
                f"Filtro '{filtro}': {len(lista_pedidos)} pedidos após filtragem Python"
            )

            return ColetaService._agrupar_por_cliente(lista_pedidos, filtro)
            
        except Exception as e:
            _app_logger().error(f"Erro ao listar pedidos para coleta: {str(e)}")
            return ColetaService._listar_pedidos_para_coleta_fallback(filtro)

    @staticmethod
    def _listar_pedidos_para_coleta_fallback(filtro: str) -> List[Dict]:
        """
        Fallback simplificado para ambientes de teste ou bancos sem suporte aos recursos SQL usados.
        """
        try:
            query = (
                Pedido.query.filter(Pedido.status.in_(ColetaService.STATUS_PEDIDOS_RELEVANTES))
                .options(db.selectinload(Pedido.cliente))
                .order_by(Pedido.data.asc())
            )
            pedidos = query.all()
        except Exception as e:
            _app_logger().error(f"Fallback de pedidos para coleta falhou: {str(e)}")
            return []

        agrupados_por_cliente: Dict[int, Dict] = {}
        for pedido in pedidos:
            itens = getattr(pedido, "itens", []) or []
            total_itens = sum(getattr(item, "quantidade", 0) or 0 for item in itens)
            itens_coletados = sum(
                getattr(item, "quantidade_coletada", 0) or 0 for item in itens
            )
            total_venda = sum(
                float(getattr(item, "valor_total_venda", 0) or 0.0) for item in itens
            )
            total_pago = float(getattr(pedido, "total_pago", 0) or 0.0)
            itens_pendentes = max(total_itens - itens_coletados, 0)
            is_coletado_completo = total_itens > 0 and itens_coletados >= total_itens

            if filtro == "pendentes" and (
                total_itens == 0 or is_coletado_completo
            ):
                continue
            if filtro == "coletados" and not is_coletado_completo:
                continue

            cliente_id = getattr(pedido.cliente, "id", None)
            chave = cliente_id if cliente_id is not None else -1

            if chave not in agrupados_por_cliente:
                agrupados_por_cliente[chave] = {
                    "pedido": pedido,
                    "pedidos_ids": [],
                    "total_itens": 0,
                    "itens_coletados": 0,
                    "itens_pendentes": 0,
                    "total_venda": 0.0,
                    "total_pago": 0.0,
                    "coletado_completo": True,
                    "pagamento_aprovado": True,
                    "data_mais_recente": pedido.data,
                }
            agrupado = agrupados_por_cliente[chave]
            agrupado["pedidos_ids"].append(pedido.id)
            agrupado["total_itens"] += total_itens
            agrupado["itens_coletados"] += itens_coletados
            agrupado["itens_pendentes"] += itens_pendentes
            agrupado["total_venda"] += total_venda
            agrupado["total_pago"] += total_pago
            agrupado["coletado_completo"] = agrupado["coletado_completo"] and is_coletado_completo
            agrupado["pagamento_aprovado"] = agrupado["pagamento_aprovado"] and getattr(pedido, "pagamento_aprovado", False)
            if pedido.data and (agrupado["data_mais_recente"] is None or pedido.data > agrupado["data_mais_recente"]):
                agrupado["data_mais_recente"] = pedido.data

        return ColetaService._agrupar_por_cliente(lista, filtro)

    @staticmethod
    def _agrupar_por_cliente(lista_pedidos: List[Dict], filtro: str) -> List[Dict]:
        """
        Consolida pedidos por cliente para simplificar o trabalho da logística.
        """
        if not lista_pedidos:
            return []

        agrupados_por_cliente: Dict[int, Dict] = {}
        for dados in lista_pedidos:
            pedido = dados.get("pedido")
            cliente = getattr(pedido, "cliente", None)
            cliente_id = getattr(cliente, "id", None)
            chave = cliente_id if cliente_id is not None else -1

            agrupado = agrupados_por_cliente.get(chave)
            if not agrupado:
                agrupado = {
                    "pedido": pedido,
                    "cliente": cliente,
                    "cliente_nome": getattr(cliente, "nome", "Cliente não identificado"),
                    "pedidos_ids": [],
                    "total_itens": 0,
                    "itens_coletados": 0,
                    "itens_pendentes": 0,
                    "total_venda": 0.0,
                    "total_pago": 0.0,
                    "coletado_completo": True,
                    "pagamento_aprovado": True,
                    "data_mais_recente": getattr(pedido, "data", None),
                }
                agrupados_por_cliente[chave] = agrupado

            agrupado["pedidos_ids"].append(getattr(pedido, "id", None))
            agrupado["total_itens"] += dados.get("total_itens", 0)
            agrupado["itens_coletados"] += dados.get("itens_coletados", 0)
            agrupado["itens_pendentes"] += dados.get("itens_pendentes", 0)
            agrupado["total_venda"] += dados.get("total_venda", 0.0)
            agrupado["total_pago"] += dados.get("total_pago", 0.0)
            agrupado["coletado_completo"] = agrupado["coletado_completo"] and dados.get("coletado_completo", False)
            agrupado["pagamento_aprovado"] = agrupado["pagamento_aprovado"] and dados.get("pagamento_aprovado", False)

            data_pedido = getattr(pedido, "data", None)
            if data_pedido and (
                agrupado["data_mais_recente"] is None or data_pedido > agrupado["data_mais_recente"]
            ):
                agrupado["data_mais_recente"] = data_pedido

        agrupados = list(agrupados_por_cliente.values())
        for agrupado in agrupados:
            total = agrupado["total_itens"]
            coletados = agrupado["itens_coletados"]
            agrupado["percentual"] = (coletados / total * 100) if total else 0
            agrupado["pedidos_ids"] = [pid for pid in agrupado["pedidos_ids"] if pid is not None]
            agrupado["pedidos_ids"].sort()

            if agrupado["coletado_completo"]:
                agrupado["status_label"] = "Coleta concluída"
                agrupado["status_badge"] = "bg-success"
            elif coletados > 0:
                agrupado["status_label"] = "Coleta parcial"
                agrupado["status_badge"] = "bg-info"
            else:
                agrupado["status_label"] = "Aguardando coleta"
                agrupado["status_badge"] = "bg-warning"

        agrupados.sort(
            key=lambda item: item["data_mais_recente"]
            or getattr(item.get("pedido"), "data", None)
            or datetime.min
        )

        if filtro == "pendentes":
            agrupados = [g for g in agrupados if g["total_itens"] > 0 and not g["coletado_completo"]]
        elif filtro == "coletados":
            agrupados = [g for g in agrupados if g["coletado_completo"]]

        return agrupados

    @staticmethod
    def listar_pendencias_por_pedidos(pedido_ids: List[int]) -> List[Dict]:
        """Agrupa quantidades pendentes por produto para os pedidos informados."""
        if not pedido_ids:
            return []

        pendencias: Dict[str, Dict[str, object]] = {}

        for pedido_id in pedido_ids:
            detalhes = ColetaService.buscar_detalhes_pedido(pedido_id)
            if not detalhes:
                continue

            for item in detalhes.get('itens', []):
                pendente = getattr(item, 'quantidade_pendente', 0) or 0
                if pendente <= 0:
                    continue

                produto = getattr(getattr(item, 'produto', None), 'nome', None) or getattr(item, 'descricao', 'Produto sem descrição')
                chave = f"{getattr(item, 'produto_id', '')}-{produto}"
                registro = pendencias.setdefault(chave, {'produto': produto, 'quantidade': 0})
                registro['quantidade'] = int(registro['quantidade']) + int(pendente)

        itens = list(pendencias.values())
        itens.sort(key=lambda registro: registro['produto'])
        return itens

    @staticmethod
    def buscar_detalhes_pedido(pedido_id: int) -> Optional[Dict]:
        """
        Busca detalhes completos de um pedido para coleta
        
        Args:
            pedido_id: ID do pedido
            
        Returns:
            Optional[Dict]: Detalhes do pedido ou None se não encontrado
        """
        try:
            pedido = (
                Pedido.query.filter(
                    Pedido.id == pedido_id,
                    Pedido.status.in_(
                        [StatusPedido.PAGAMENTO_APROVADO, StatusPedido.COLETA_PARCIAL]
                    ),
                )
                .options(
                    db.joinedload(Pedido.cliente),
                    db.joinedload(Pedido.itens).joinedload(ItemPedido.produto),
                )
                .first()
            )
        except Exception as e:
            _app_logger().error(f"Erro ao buscar detalhes do pedido {pedido_id}: {str(e)}")
            return ColetaService._buscar_detalhes_pedido_fallback(pedido_id)

        if not pedido:
            return None

        # Calcular quantidades já coletadas e pendentes
        for item in getattr(pedido, "itens", []):
            try:
                total_coletado = (
                    db.session.query(func.coalesce(func.sum(ItemColetado.quantidade_coletada), 0))
                    .join(Coleta)
                    .filter(Coleta.pedido_id == pedido.id, ItemColetado.item_pedido_id == item.id)
                    .scalar()
                )
            except Exception:
                total_coletado = getattr(item, "quantidade_coletada", 0) or 0

            item.quantidade_coletada = total_coletado
            item.quantidade_pendente = (getattr(item, "quantidade", 0) or 0) - total_coletado

            try:
                estoque = Estoque.query.filter_by(produto_id=item.produto_id).first()
            except Exception:
                estoque = None

            item.estoque_disponivel = getattr(estoque, "quantidade", 0)
            item.quantidade_maxima_coleta = min(
                max(item.quantidade_pendente, 0), item.estoque_disponivel
            )

        return {
            "pedido": pedido,
            "cliente": getattr(pedido, "cliente", None),
            "itens": pedido.itens,
        }

    @staticmethod
    def _buscar_detalhes_pedido_fallback(pedido_id: int) -> Optional[Dict]:
        """
        Retorna detalhes básicos do pedido sem executar consultas avançadas (usado em testes).
        """
        try:
            pedido = Pedido.query.filter(Pedido.id == pedido_id).first()
        except Exception as e:
            _app_logger().error(f"Fallback de detalhes do pedido {pedido_id} falhou: {str(e)}")
            return None

        if not pedido:
            return None

        for item in getattr(pedido, "itens", []):
            quantidade = getattr(item, "quantidade", 0) or 0
            coletada = getattr(item, "quantidade_coletada", 0) or 0
            item.quantidade_coletada = coletada
            item.quantidade_pendente = max(quantidade - coletada, 0)
            estoque_disponivel = getattr(item, "estoque_disponivel", 0) or 0
            item.estoque_disponivel = estoque_disponivel
            item.quantidade_maxima_coleta = min(item.quantidade_pendente, estoque_disponivel)

        return {
            "pedido": pedido,
            "cliente": getattr(pedido, "cliente", None),
            "itens": pedido.itens,
        }

    @staticmethod
    def processar_coleta(
        pedido_id: int,
        responsavel_coleta_id: int,
        nome_retirada: str,
        documento_retirada: str,
        itens_coleta: List[Dict],
        observacoes: str = None,
        nome_conferente: str = None,
        cpf_conferente: str = None
    ) -> Tuple[bool, str, Optional[Coleta]]:
        """
        Processa uma nova coleta (funcionalidade unificada)
        
        Args:
            pedido_id: ID do pedido
            responsavel_coleta_id: ID do usuário responsável pela coleta
            nome_retirada: Nome de quem está retirando
            documento_retirada: CPF de quem está retirando
            itens_coleta: Lista de itens e quantidades a coletar
            observacoes: Observações opcionais
            nome_conferente: Nome do conferente
            cpf_conferente: CPF do conferente
            
        Returns:
            Tuple[bool, str, Optional[Coleta]]: (sucesso, mensagem, coleta)
        """
        try:
            # Validar dados básicos
            if not nome_retirada or not documento_retirada:
                return False, "Nome e documento da retirada são obrigatórios", None
            
            if not itens_coleta:
                return False, "Selecione pelo menos um item para coleta", None
            
            # Buscar pedido com lock para evitar race conditions
            pedido = db.session.query(Pedido).filter(
                Pedido.id == pedido_id
            ).with_for_update().first()
            
            if not pedido or pedido.status not in [StatusPedido.PAGAMENTO_APROVADO, StatusPedido.COLETA_PARCIAL]:
                return False, "Pedido não encontrado ou não disponível para coleta", None
            
            # Validar itens e quantidades
            for item_data in itens_coleta:
                item_id = item_data.get('item_id')
                quantidade = item_data.get('quantidade', 0)
                
                if quantidade <= 0:
                    continue
                
                # Buscar item do pedido com lock
                item_pedido = db.session.query(ItemPedido).filter(
                    ItemPedido.id == item_id,
                    ItemPedido.pedido_id == pedido_id
                ).with_for_update().first()
                
                if not item_pedido:
                    return False, f"Item {item_id} não encontrado no pedido", None
                
                # Calcular quantidade já coletada
                total_coletado_item = db.session.query(
                    func.coalesce(func.sum(ItemColetado.quantidade_coletada), 0)
                ).join(Coleta).filter(
                    Coleta.pedido_id == pedido.id,
                    ItemColetado.item_pedido_id == item_pedido.id
                ).scalar()
                
                quantidade_pendente = item_pedido.quantidade - total_coletado_item
                
                # Validar se não excede o pendente
                if quantidade > quantidade_pendente:
                    return False, f"Quantidade {quantidade} excede o pendente {quantidade_pendente} para {item_pedido.produto.nome}", None
                
                # Validar estoque com lock
                estoque = db.session.query(Estoque).filter_by(
                    produto_id=item_pedido.produto_id
                ).with_for_update().first()
                
                if estoque and quantidade > estoque.quantidade:
                    return False, f"Quantidade {quantidade} excede o estoque disponível {estoque.quantidade} para {item_pedido.produto.nome}", None
            
            # Determinar status da coleta
            total_pendente_geral = 0
            for item_pedido in pedido.itens:
                total_coletado_item = db.session.query(
                    func.coalesce(func.sum(ItemColetado.quantidade_coletada), 0)
                ).join(Coleta).filter(
                    Coleta.pedido_id == pedido.id,
                    ItemColetado.item_pedido_id == item_pedido.id
                ).scalar()
                total_pendente_geral += item_pedido.quantidade - total_coletado_item

            total_coletado_nesta_vez = sum(item_data.get('quantidade', 0) for item_data in itens_coleta)
            
            if total_coletado_nesta_vez >= total_pendente_geral:
                status_coleta = StatusColeta.TOTALMENTE_COLETADO
                status_pedido = StatusPedido.COLETA_CONCLUIDA
            else:
                status_coleta = StatusColeta.PARCIALMENTE_COLETADO
                status_pedido = StatusPedido.COLETA_PARCIAL
            
            # Criar registro de coleta
            nova_coleta = Coleta(
                pedido_id=pedido_id,
                responsavel_coleta_id=responsavel_coleta_id,
                nome_retirada=nome_retirada,
                documento_retirada=documento_retirada,
                status=status_coleta,
                observacoes=observacoes,
                nome_conferente=nome_conferente,
                cpf_conferente=cpf_conferente
            )
            
            db.session.add(nova_coleta)
            db.session.flush()  # Para obter o ID da coleta
        
            # Criar registros de itens coletados e dar baixa no estoque
            for item_data in itens_coleta:
                quantidade = item_data.get('quantidade', 0)
                if quantidade > 0:
                    item_coletado = ItemColetado(
                        coleta_id=nova_coleta.id,
                        item_pedido_id=item_data['item_id'],
                        quantidade_coletada=quantidade
                    )
                    db.session.add(item_coletado)
                    
                    # Dar baixa no estoque
                    ColetaService._registrar_movimentacao_estoque(
                        item_data['item_id'],
                        quantidade,
                        nome_retirada
                    )
            
            # Atualizar status do pedido
            pedido.status = status_pedido
            
            # Commit da transação
            db.session.commit()
            
            _app_logger().info(
                f"Coleta processada: ID {nova_coleta.id}, Pedido {pedido_id}, Status {status_coleta.value}"
            )
            
            return True, f"Coleta registrada com sucesso. Status: {status_coleta.value}", nova_coleta
            
        except Exception as e:
            db.session.rollback()
            _app_logger().error(f"Erro ao processar coleta: {str(e)}")
            return False, f"Erro ao processar coleta: {str(e)}", None

    @staticmethod
    def _registrar_movimentacao_estoque(item_pedido_id: int, quantidade: int, responsavel: str):
        """
        Registra movimentação de estoque para uma coleta
        
        Args:
            item_pedido_id: ID do item do pedido
            quantidade: Quantidade coletada
            responsavel: Nome do responsável
        """
        try:
            bind = db.session.get_bind()
            dialect = getattr(bind, "dialect", None)
            supports_for_update = bool(getattr(dialect, "supports_for_update", False))
            enforce_lock = not _app_debug() and not _app_config_get("TESTING", False)
            if not supports_for_update:
                detalhes_lock = {
                    "dialeto": getattr(dialect, "name", "desconhecido") if dialect else "desconhecido",
                    "feature": "supports_for_update",
                }
                if enforce_lock:
                    raise ConfigurationError(
                        message="Banco de dados configurado não suporta SELECT ... FOR UPDATE para controle de estoque",
                        details=detalhes_lock,
                    )
                _app_logger().warning(
                    "Banco atual não suporta bloqueio pessimista; usando fallback otimista",
                    extra=detalhes_lock,
                )
            
            # Buscar item do pedido com lock
            item_pedido = (
                db.session.query(ItemPedido)
                .options(db.joinedload(ItemPedido.produto))
                .filter(ItemPedido.id == item_pedido_id)
                .with_for_update()
                .first()
            )
            
            if not item_pedido:
                raise EstoqueError(
                    message="Item do pedido não encontrado para movimentação de estoque",
                    details={"item_pedido_id": item_pedido_id},
                )
            
            if quantidade <= 0:
                raise EstoqueError(
                    message="Quantidade inválida para movimentação de estoque",
                    details={"quantidade": quantidade, "item_pedido_id": item_pedido_id},
                )
            
            produto_id = item_pedido.produto_id
            
            # Buscar estoque atual com lock
            estoque = (
                db.session.query(Estoque)
                .filter_by(produto_id=produto_id)
                .with_for_update()
                .first()
            )
            
            if not estoque:
                raise EstoqueError(
                    message="Estoque inexistente para o produto da movimentação",
                    details={"produto_id": produto_id, "item_pedido_id": item_pedido_id},
                )
            
            # Calcular novas quantidades
            quantidade_anterior = estoque.quantidade
            quantidade_atual = quantidade_anterior - quantidade
            
            if quantidade_atual < 0:
                raise EstoqueError(
                    message="Movimentação resultaria em estoque negativo",
                    details={
                        "produto_id": produto_id,
                        "item_pedido_id": item_pedido_id,
                        "quantidade_disponivel": quantidade_anterior,
                        "quantidade_solicitada": quantidade,
                    },
                )
            
            # Criar movimentação
            movimentacao = MovimentacaoEstoque(
                produto_id=produto_id,
                tipo_movimentacao="Saída",
                quantidade_anterior=quantidade_anterior,
                quantidade_movimentada=-quantidade,  # Negativo para saída
                quantidade_atual=quantidade_atual,
                motivo=f"Saída por coleta - Responsável: {responsavel}",
                responsavel=responsavel,
                observacoes=f"Coleta do item {item_pedido_id}"
            )
            
            db.session.add(movimentacao)
            
            # Atualizar estoque
            estoque.quantidade = quantidade_atual
            
            _app_logger().info(
                f"Movimentação de estoque registrada: {item_pedido.produto.nome} - Saída: {quantidade}"
            )
            
        except EstoqueError as erro:
            detalhes = getattr(erro, "details", {}) or {}
            _app_logger().warning(
                f"Erro de estoque ao registrar movimentação: {erro.message} | Detalhes: {detalhes}"
            )
            raise
        except Exception as e:
            _app_logger().error(f"Erro ao registrar movimentação de estoque: {str(e)}")
            raise EstoqueError(
                message="Erro inesperado ao registrar movimentação de estoque",
                details={"item_pedido_id": item_pedido_id, "error": str(e)},
            )

    @staticmethod
    def buscar_historico_coletas(pedido_id: int) -> Optional[Dict]:
        """
        Busca o histórico de coletas de um pedido.

        Args:
            pedido_id: ID do pedido.

        Returns:
            Optional[Dict]: Dicionário com o histórico do pedido ou None.
        """
        try:
            pedido = db.session.query(Pedido).filter(Pedido.id == pedido_id).first()
            if not pedido:
                return None

            coletas = Coleta.query.filter_by(pedido_id=pedido_id).order_by(Coleta.data_coleta.desc()).all()

            return {
                'pedido': pedido,
                'coletas': coletas
            }
        except Exception as e:
            _app_logger().error(f"Erro ao buscar histórico de coletas: {str(e)}")
            return None

    @staticmethod
    def listar_pedidos_coletados() -> List[Dict]:
        """
        Lista pedidos que já foram coletados (funcionalidade do logística)
        
        Returns:
            List[Dict]: Lista de pedidos coletados
        """
        try:
            pedidos = Pedido.query.join(Coleta).distinct().all()
            pedidos_info = []

            for pedido in pedidos:
                # Soma da quantidade total do pedido
                qtd_total = sum(item.quantidade for item in pedido.itens)
                # Soma da quantidade coletada
                qtd_coletada = db.session.query(db.func.sum(ItemColetado.quantidade_coletada))\
                    .join(ItemPedido)\
                    .filter(ItemPedido.pedido_id == pedido.id).scalar() or 0
                # Soma do valor total do pedido
                total_venda = sum([item.valor_total_venda for item in pedido.itens])
                pedidos_info.append((pedido, qtd_total, qtd_coletada, total_venda))

            return pedidos_info
            
        except Exception as e:
            _app_logger().error(f"Erro ao listar pedidos coletados: {str(e)}")
            return []
