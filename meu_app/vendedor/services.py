from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import func, desc
from meu_app.models import Cliente, Pedido, ItemPedido, Produto
from meu_app import db
from meu_app.time_utils import local_now_naive

class VendedorService:
    
    @staticmethod
    def get_clientes_por_atividade():
        """
        Organiza clientes em 4 categorias baseadas na data da última compra
        """
        from meu_app.models import StatusPedido
        hoje = local_now_naive().date()
        
        # Buscar todos os clientes com dados de última compra (apenas pedidos completamente pagos)
        # Primeiro, buscar a data da última compra de cada cliente
        clientes_ultima_compra = db.session.query(
            Cliente.id,
            Cliente.nome,
            Cliente.fantasia,
            Cliente.telefone,
            func.max(Pedido.data).label('ultima_compra')
        ).join(Pedido, Cliente.id == Pedido.cliente_id)\
         .filter(Pedido.status.in_([
            StatusPedido.PAGAMENTO_APROVADO,
            StatusPedido.COLETA_PARCIAL,
            StatusPedido.COLETA_CONCLUIDA
        ]))\
         .group_by(Cliente.id, Cliente.nome, Cliente.fantasia, Cliente.telefone)\
         .all()
        
        # Para cada cliente, buscar o valor da última compra
        clientes_com_pedidos = []
        for cliente in clientes_ultima_compra:
            # Buscar o valor total do último pedido (apenas pedidos completamente pagos)
            ultimo_pedido = db.session.query(Pedido).filter(
                Pedido.cliente_id == cliente.id,
                Pedido.data == cliente.ultima_compra,
                Pedido.status.in_([
                    StatusPedido.PAGAMENTO_APROVADO,
                    StatusPedido.COLETA_PARCIAL,
                    StatusPedido.COLETA_CONCLUIDA
                ])
            ).first()
            
            if ultimo_pedido:
                # Calcular valor total dos itens do último pedido
                valor_ultima_compra = db.session.query(
                    func.sum(ItemPedido.valor_total_venda)
                ).filter(ItemPedido.pedido_id == ultimo_pedido.id).scalar() or 0
            else:
                valor_ultima_compra = 0
            
            clientes_com_pedidos.append({
                'id': cliente.id,
                'nome': cliente.nome,
                'fantasia': cliente.fantasia,
                'telefone': cliente.telefone,
                'ultima_compra': cliente.ultima_compra,
                'valor_ultima_compra': float(valor_ultima_compra)
            })
        
        # Categorizar clientes
        ativos = []
        atencao = []
        em_risco = []
        inativos = []
        
        for cliente in clientes_com_pedidos:
            dias_desde_ultima_compra = (hoje - cliente['ultima_compra'].date()).days
            
            cliente_data = {
                'id': cliente['id'],
                'nome': cliente['nome'],
                'fantasia': cliente['fantasia'],
                'telefone': cliente['telefone'],
                'ultima_compra': cliente['ultima_compra'],
                'valor_ultima_compra': cliente['valor_ultima_compra'],
                'dias_sem_comprar': dias_desde_ultima_compra
            }
            
            if dias_desde_ultima_compra <= 7:
                ativos.append(cliente_data)
            elif dias_desde_ultima_compra <= 14:
                atencao.append(cliente_data)
            elif dias_desde_ultima_compra <= 30:
                em_risco.append(cliente_data)
            else:
                inativos.append(cliente_data)
        
        # Buscar clientes sem pedidos
        clientes_sem_pedidos = db.session.query(Cliente).filter(
            ~Cliente.id.in_([c['id'] for c in clientes_com_pedidos])
        ).all()
        
        for cliente in clientes_sem_pedidos:
            cliente_data = {
                'id': cliente.id,
                'nome': cliente.nome,
                'fantasia': cliente.fantasia,
                'telefone': cliente.telefone,
                'ultima_compra': None,
                'valor_ultima_compra': 0,
                'dias_sem_comprar': None
            }
            inativos.append(cliente_data)
        
        return {
            'ativos': ativos,
            'atencao': atencao,
            'em_risco': em_risco,
            'inativos': inativos
        }
    
    @staticmethod
    def get_detalhes_cliente(cliente_id):
        """
        Retorna detalhes completos de um cliente
        """
        cliente = Cliente.query.get_or_404(cliente_id)
        
        # Buscar apenas pedidos completamente pagos do cliente
        from meu_app.models import StatusPedido
        
        pedidos = Pedido.query.filter_by(cliente_id=cliente_id)\
                             .filter(Pedido.status.in_([
                                StatusPedido.PAGAMENTO_APROVADO,
                                StatusPedido.COLETA_PARCIAL,
                                StatusPedido.COLETA_CONCLUIDA
                             ]))\
                             .order_by(desc(Pedido.data)).all()
        
        # Calcular estatísticas
        total_gasto = 0
        for pedido in pedidos:
            valor_pedido = db.session.query(
                func.sum(ItemPedido.valor_total_venda)
            ).filter(ItemPedido.pedido_id == pedido.id).scalar() or 0
            total_gasto += float(valor_pedido)
        
        total_pedidos = len(pedidos)
        ticket_medio = total_gasto / total_pedidos if total_pedidos > 0 else 0
        
        # Produtos diferentes comprados (apenas em pedidos completamente pagos)
        produtos_diferentes = db.session.query(
            func.count(func.distinct(ItemPedido.produto_id))
        ).join(Pedido, ItemPedido.pedido_id == Pedido.id)\
         .filter(
            Pedido.cliente_id == cliente_id,
            Pedido.status.in_([
                StatusPedido.PAGAMENTO_APROVADO,
                StatusPedido.COLETA_PARCIAL,
                StatusPedido.COLETA_CONCLUIDA
            ])
         ).scalar() or 0
        
        # Primeiro e último pedido
        primeiro_pedido = pedidos[-1] if pedidos else None
        ultimo_pedido = pedidos[0] if pedidos else None
        
        # Detalhes dos pedidos
        pedidos_detalhados = []
        for pedido in pedidos:
            itens = ItemPedido.query.filter_by(pedido_id=pedido.id).all()
            
            itens_detalhados = []
            for item in itens:
                itens_detalhados.append({
                    'quantidade': item.quantidade,
                    'produto_nome': item.produto.nome,
                    'preco_unitario': float(item.preco_venda),
                    'subtotal': float(item.valor_total_venda)
                })
            
            # Calcular valor total do pedido
            valor_total_pedido = db.session.query(
                func.sum(ItemPedido.valor_total_venda)
            ).filter(ItemPedido.pedido_id == pedido.id).scalar() or 0
            
            pedidos_detalhados.append({
                'id': pedido.id,
                'data': pedido.data,
                'valor_total': float(valor_total_pedido),
                'status': pedido.status.value if pedido.status else 'N/A',
                'itens': itens_detalhados
            })
        
        return {
            'cliente': cliente,
            'estatisticas': {
                'total_gasto': total_gasto,
                'total_pedidos': total_pedidos,
                'ticket_medio': ticket_medio,
                'produtos_diferentes': produtos_diferentes,
                'primeiro_pedido': primeiro_pedido,
                'ultimo_pedido': ultimo_pedido
            },
            'pedidos': pedidos_detalhados
        }
    
    @staticmethod
    @staticmethod
    def _parse_data_param(valor):
        """
        Converte string YYYY-MM-DD em date.
        """
        if not valor:
            return None
        try:
            return datetime.strptime(valor, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return None

    @staticmethod
    def get_rankings(periodo='todos', data_inicio=None, data_fim=None):
        """
        Retorna rankings de clientes
        """
        # Determinar intervalo de datas
        inicio_personalizado = VendedorService._parse_data_param(data_inicio)
        fim_personalizado = VendedorService._parse_data_param(data_fim)

        if inicio_personalizado and fim_personalizado and inicio_personalizado > fim_personalizado:
            inicio_personalizado, fim_personalizado = fim_personalizado, inicio_personalizado

        filtro_data_inicio = None
        filtro_data_fim = None

        if inicio_personalizado or fim_personalizado:
            filtro_data_inicio = datetime.combine(inicio_personalizado, datetime.min.time()) if inicio_personalizado else None
            filtro_data_fim = datetime.combine(fim_personalizado, datetime.max.time()) if fim_personalizado else None
        elif periodo != 'todos':
            hoje = local_now_naive().date()
            if periodo == 'ultimo_mes':
                filtro = hoje - timedelta(days=30)
            elif periodo == 'ultimos_3_meses':
                filtro = hoje - timedelta(days=90)
            elif periodo == 'ultimos_6_meses':
                filtro = hoje - timedelta(days=180)
            elif periodo == 'ultimo_ano':
                filtro = hoje - timedelta(days=365)
            else:
                filtro = None

            if filtro:
                filtro_data_inicio = datetime.combine(filtro, datetime.min.time())
                filtro_data_fim = datetime.combine(hoje, datetime.max.time())
        
        # Query base - buscar clientes com pedidos completamente pagos
        from meu_app.models import StatusPedido
        
        query = db.session.query(
            Cliente.id,
            Cliente.nome,
            func.count(Pedido.id).label('total_pedidos')
        ).join(Pedido, Cliente.id == Pedido.cliente_id)\
         .filter(Pedido.status.in_([
            StatusPedido.PAGAMENTO_APROVADO,
            StatusPedido.COLETA_PARCIAL,
            StatusPedido.COLETA_CONCLUIDA
        ]))
        
        if filtro_data_inicio:
            query = query.filter(Pedido.data >= filtro_data_inicio)
        if filtro_data_fim:
            query = query.filter(Pedido.data <= filtro_data_fim)
        
        clientes_data = query.group_by(Cliente.id, Cliente.nome).all()
        
        # Calcular valores totais e custos para cada cliente
        clientes_com_valores = []
        for cliente_data in clientes_data:
            # Calcular valor total (receita) - apenas pedidos completamente pagos
            valor_total = db.session.query(
                func.sum(ItemPedido.valor_total_venda)
            ).join(Pedido, ItemPedido.pedido_id == Pedido.id)\
             .filter(
                Pedido.cliente_id == cliente_data.id,
                Pedido.status.in_([
                    StatusPedido.PAGAMENTO_APROVADO,
                    StatusPedido.COLETA_PARCIAL,
                    StatusPedido.COLETA_CONCLUIDA
                ])
            )
            
            if filtro_data_inicio:
                valor_total = valor_total.filter(Pedido.data >= filtro_data_inicio)
            if filtro_data_fim:
                valor_total = valor_total.filter(Pedido.data <= filtro_data_fim)
            
            valor_total = valor_total.scalar() or 0
            
            # Calcular custo total (CPV) - apenas pedidos completamente pagos
            custo_total = db.session.query(
                func.sum(ItemPedido.quantidade * func.coalesce(Produto.preco_medio_compra, 0))
            ).join(Pedido, ItemPedido.pedido_id == Pedido.id)\
             .outerjoin(Produto, Produto.id == ItemPedido.produto_id)\
             .filter(
                Pedido.cliente_id == cliente_data.id,
                Pedido.status.in_([
                    StatusPedido.PAGAMENTO_APROVADO,
                    StatusPedido.COLETA_PARCIAL,
                    StatusPedido.COLETA_CONCLUIDA
                ])
            )
            
            if filtro_data_inicio:
                custo_total = custo_total.filter(Pedido.data >= filtro_data_inicio)
            if filtro_data_fim:
                custo_total = custo_total.filter(Pedido.data <= filtro_data_fim)
            
            custo_total = custo_total.scalar() or 0
            
            clientes_com_valores.append({
                'id': cliente_data.id,
                'nome': cliente_data.nome,
                'valor_total': float(valor_total),
                'total_pedidos': cliente_data.total_pedidos,
                'custo_total': float(custo_total)
            })
        
        # Ranking por faturamento
        ranking_faturamento = sorted(
            clientes_com_valores, 
            key=lambda x: x['valor_total'], 
            reverse=True
        )[:20]
        
        # Ranking por diversidade (produtos diferentes)
        ranking_diversidade = []
        for cliente_data in clientes_com_valores:
            produtos_diferentes = db.session.query(
                func.count(func.distinct(ItemPedido.produto_id))
            ).join(Pedido, ItemPedido.pedido_id == Pedido.id)\
             .filter(Pedido.cliente_id == cliente_data['id'])
            
            if filtro_data_inicio:
                produtos_diferentes = produtos_diferentes.filter(Pedido.data >= filtro_data_inicio)
            if filtro_data_fim:
                produtos_diferentes = produtos_diferentes.filter(Pedido.data <= filtro_data_fim)
            
            produtos_diferentes = produtos_diferentes.scalar() or 0
            
            ranking_diversidade.append({
                'id': cliente_data['id'],
                'nome': cliente_data['nome'],
                'produtos_diferentes': produtos_diferentes,
                'valor_total': cliente_data['valor_total']
            })
        
        ranking_diversidade = sorted(
            ranking_diversidade,
            key=lambda x: x['produtos_diferentes'],
            reverse=True
        )[:20]
        
        # Ranking por margem de lucro
        ranking_margem = []
        for cliente_data in clientes_com_valores:
            lucro_total = cliente_data['valor_total'] - cliente_data['custo_total']
            margem_media = (lucro_total / cliente_data['valor_total']) * 100 if cliente_data['valor_total'] > 0 else 0
            
            ranking_margem.append({
                'id': cliente_data['id'],
                'nome': cliente_data['nome'],
                'lucro_total': lucro_total,
                'margem_media': margem_media
            })
        
        ranking_margem = sorted(
            ranking_margem,
            key=lambda x: x['lucro_total'],
            reverse=True
        )[:20]
        
        return {
            'faturamento': ranking_faturamento,
            'diversidade': ranking_diversidade,
            'margem': ranking_margem,
            'intervalo': {
                'inicio': inicio_personalizado.strftime('%d/%m/%Y') if inicio_personalizado else (filtro_data_inicio.strftime('%d/%m/%Y') if filtro_data_inicio else None),
                'fim': fim_personalizado.strftime('%d/%m/%Y') if fim_personalizado else (filtro_data_fim.strftime('%d/%m/%Y') if filtro_data_fim else None)
            }
        }
    
    @staticmethod
    def get_resumo_dashboard():
        """
        Retorna resumo geral do dashboard
        """
        from meu_app.models import StatusPedido
        hoje = local_now_naive().date()
        
        # Total de clientes
        total_clientes = Cliente.query.count()
        
        # Clientes com última compra (apenas pedidos completamente pagos)
        clientes_ultima_compra = db.session.query(
            Cliente.id,
            func.max(Pedido.data).label('ultima_compra')
        ).join(Pedido, Cliente.id == Pedido.cliente_id)\
         .filter(Pedido.status.in_([
            StatusPedido.PAGAMENTO_APROVADO,
            StatusPedido.COLETA_PARCIAL,
            StatusPedido.COLETA_CONCLUIDA
        ]))\
         .group_by(Cliente.id).all()
        
        # Categorizar por período
        sem_compra_7_dias = []
        sem_compra_15_dias = []
        sem_compra_30_dias = []
        
        for cliente in clientes_ultima_compra:
            dias = (hoje - cliente.ultima_compra.date()).days
            
            if 7 < dias <= 15:
                sem_compra_7_dias.append(cliente.id)
            elif 15 < dias <= 30:
                sem_compra_15_dias.append(cliente.id)
            elif dias > 30:
                sem_compra_30_dias.append(cliente.id)

        clientes_fieis = len(VendedorService.get_clientes_por_periodo('fieis'))

        return {
            'total_clientes': total_clientes,
            'clientes_fieis': clientes_fieis,
            'sem_compra_7_dias': len(sem_compra_7_dias),
            'sem_compra_15_dias': len(sem_compra_15_dias),
            'sem_compra_30_dias': len(sem_compra_30_dias)
        }
    
    @staticmethod
    def get_clientes_por_periodo(periodo):
        """
        Retorna lista de clientes baseado no período sem comprar
        periodo: 'todos', '7', '15', '30', 'fieis'
        """
        from meu_app.models import StatusPedido
        hoje = local_now_naive().date()
        
        # Buscar clientes com última compra (apenas pedidos completamente pagos)
        clientes_query = db.session.query(
            Cliente.id,
            Cliente.nome,
            Cliente.fantasia,
            Cliente.telefone,
            func.max(Pedido.data).label('ultima_compra')
        ).join(Pedido, Cliente.id == Pedido.cliente_id)\
         .filter(Pedido.status.in_([
            StatusPedido.PAGAMENTO_APROVADO,
            StatusPedido.COLETA_PARCIAL,
            StatusPedido.COLETA_CONCLUIDA
        ]))\
         .group_by(Cliente.id, Cliente.nome, Cliente.fantasia, Cliente.telefone)
        
        clientes = clientes_query.all()
        if periodo in ('7', '15', '30'):
            # Filtrar por período
            dias_min = 0
            dias_max = 999999
            
            if periodo == '7':
                dias_min = 7
                dias_max = 15
            elif periodo == '15':
                dias_min = 15
                dias_max = 30
            elif periodo == '30':
                dias_min = 30
            
            clientes = [
                c for c in clientes
                if dias_min < (hoje - c.ultima_compra.date()).days <= dias_max
            ]
        
        # Buscar valor da última compra
        resultado = []
        limite_fieis = 5
        for cliente in clientes:
            ultimo_pedido = Pedido.query.filter_by(cliente_id=cliente.id)\
                                        .filter(Pedido.status.in_([
                                            StatusPedido.PAGAMENTO_APROVADO,
                                            StatusPedido.COLETA_PARCIAL,
                                            StatusPedido.COLETA_CONCLUIDA
                                        ]))\
                                        .order_by(Pedido.data.desc()).first()
            
            if ultimo_pedido:
                valor_ultima = db.session.query(
                    func.sum(ItemPedido.valor_total_venda)
                ).filter(ItemPedido.pedido_id == ultimo_pedido.id).scalar() or 0
            else:
                valor_ultima = 0
            
            dias_sem_comprar = (hoje - cliente.ultima_compra.date()).days

            pedidos_cliente = Pedido.query.filter_by(cliente_id=cliente.id)\
                                          .filter(Pedido.status.in_([
                                              StatusPedido.PAGAMENTO_APROVADO,
                                              StatusPedido.COLETA_PARCIAL,
                                              StatusPedido.COLETA_CONCLUIDA
                                          ]))\
                                          .order_by(Pedido.data.desc()).all()

            recorrencia_media = None
            if len(pedidos_cliente) > 1:
                datas = [p.data.date() for p in pedidos_cliente]
                diffs = [
                    (datas[idx] - datas[idx + 1]).days
                    for idx in range(len(datas) - 1)
                    if (datas[idx] - datas[idx + 1]).days >= 0
                ]
                if diffs:
                    recorrencia_media = sum(diffs) / len(diffs)

            if periodo == 'fieis':
                if recorrencia_media is None or recorrencia_media >= limite_fieis:
                    continue
            
            ultima_compra_iso = cliente.ultima_compra.isoformat() if cliente.ultima_compra else None
            resultado.append({
                'id': cliente.id,
                'nome': cliente.nome,
                'fantasia': cliente.fantasia,
                'telefone': cliente.telefone,
                'ultima_compra': ultima_compra_iso,
                'valor_ultima_compra': float(valor_ultima),
                'dias_sem_comprar': dias_sem_comprar,
                'total_pedidos': len(pedidos_cliente),
                'recorrencia_media_dias': float(recorrencia_media) if recorrencia_media is not None else None
            })
        
        return sorted(resultado, key=lambda x: x['dias_sem_comprar'], reverse=True)
    
    @staticmethod
    def get_ranking_produtos(limite=10, data_inicio=None, data_fim=None):
        """
        Retorna ranking de produtos por valor vendido (apenas pedidos completamente pagos)
        """
        from meu_app.models import StatusPedido
        inicio = VendedorService._parse_data_param(data_inicio)
        fim = VendedorService._parse_data_param(data_fim)
        if inicio and fim and inicio > fim:
            inicio, fim = fim, inicio
        inicio_dt = datetime.combine(inicio, datetime.min.time()) if inicio else None
        fim_dt = datetime.combine(fim, datetime.max.time()) if fim else None

        ranking_query = db.session.query(
            Produto.id,
            Produto.nome,
            func.sum(ItemPedido.valor_total_venda).label('valor_total'),
            func.sum(ItemPedido.quantidade).label('quantidade_total')
        ).join(ItemPedido, Produto.id == ItemPedido.produto_id)\
         .join(Pedido, ItemPedido.pedido_id == Pedido.id)\
         .filter(Pedido.status.in_([
            StatusPedido.PAGAMENTO_APROVADO,
            StatusPedido.COLETA_PARCIAL,
            StatusPedido.COLETA_CONCLUIDA
        ]))

        if inicio_dt:
            ranking_query = ranking_query.filter(Pedido.data >= inicio_dt)
        if fim_dt:
            ranking_query = ranking_query.filter(Pedido.data <= fim_dt)

        ranking = ranking_query.group_by(Produto.id, Produto.nome)\
                               .order_by(desc(func.sum(ItemPedido.valor_total_venda)))\
                               .limit(limite).all()

        resultados = []
        for p in ranking:
            quantidade_total = int(p.quantidade_total or 0)
            valor_total = float(p.valor_total or 0)
            preco_medio = valor_total / quantidade_total if quantidade_total else 0.0
            resultados.append({
                'id': p.id,
                'nome': p.nome,
                'preco_medio': preco_medio
            })

        return resultados
    
    @staticmethod
    def get_pedidos_cliente(cliente_id):
        """
        Retorna lista de pedidos de um cliente (apenas pedidos completamente pagos)
        """
        from meu_app.models import StatusPedido
        pedidos = Pedido.query.filter_by(cliente_id=cliente_id)\
                             .filter(Pedido.status.in_([
                                StatusPedido.PAGAMENTO_APROVADO,
                                StatusPedido.COLETA_PARCIAL,
                                StatusPedido.COLETA_CONCLUIDA
                             ]))\
                             .order_by(desc(Pedido.data)).all()
        
        resultado = []
        for pedido in pedidos:
            valor_total = db.session.query(
                func.sum(ItemPedido.valor_total_venda)
            ).filter(ItemPedido.pedido_id == pedido.id).scalar() or 0
            
            resultado.append({
                'id': pedido.id,
                'data': pedido.data.strftime('%d/%m/%Y'),
                'valor_total': float(valor_total),
                'status': pedido.status.value if pedido.status else 'N/A'
            })
        
        return resultado
    
    @staticmethod
    def get_produtos_cliente(cliente_id):
        """
        Retorna lista de produtos compilados comprados por um cliente (apenas pedidos completamente pagos)
        """
        from meu_app.models import StatusPedido
        produtos = db.session.query(
            Produto.nome,
            func.sum(ItemPedido.quantidade).label('quantidade_total'),
            func.avg(ItemPedido.preco_venda).label('preco_medio'),
            func.max(Pedido.data).label('ultima_compra')
        ).join(ItemPedido, Produto.id == ItemPedido.produto_id)\
         .join(Pedido, ItemPedido.pedido_id == Pedido.id)\
         .filter(
            Pedido.cliente_id == cliente_id,
            Pedido.status.in_([
                StatusPedido.PAGAMENTO_APROVADO,
                StatusPedido.COLETA_PARCIAL,
                StatusPedido.COLETA_CONCLUIDA
            ])
         )\
         .group_by(Produto.nome)\
         .order_by(desc(func.sum(ItemPedido.quantidade)))\
         .all()
        
        return [{
            'produto': p.nome,
            'quantidade_total': p.quantidade_total,
            'preco_medio': float(p.preco_medio),
            'ultima_compra': p.ultima_compra.strftime('%d/%m/%Y')
        } for p in produtos]

    @staticmethod
    def get_precos_negociados(cliente_id, limite=30):
        """
        Retorna os últimos preços negociados por produto para um cliente
        """
        from meu_app.models import StatusPedido
        itens = db.session.query(
            Produto.nome.label('produto'),
            ItemPedido.preco_venda.label('preco'),
            Pedido.data.label('data')
        ).join(Produto, ItemPedido.produto_id == Produto.id)\
         .join(Pedido, ItemPedido.pedido_id == Pedido.id)\
         .filter(
            Pedido.cliente_id == cliente_id,
            Pedido.status.in_([
                StatusPedido.PAGAMENTO_APROVADO,
                StatusPedido.COLETA_PARCIAL,
                StatusPedido.COLETA_CONCLUIDA
            ])
         )\
         .order_by(desc(Pedido.data), desc(ItemPedido.id))\
         .limit(limite)\
         .all()

        return [{
            'produto': item.produto,
            'preco': float(item.preco or 0),
            'data': item.data.strftime('%d/%m/%Y')
        } for item in itens]
