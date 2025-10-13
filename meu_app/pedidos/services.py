"""
Serviços para o módulo de pedidos
Contém toda a lógica de negócio complexa separada das rotas
"""
from ..models import db, Pedido, ItemPedido, Cliente, Produto, Coleta, ItemColetado, LogAtividade, Usuario
from flask import current_app, session
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import pandas as pd
import unicodedata

class PedidoService:
    """Serviço para operações relacionadas a pedidos"""
    
    @staticmethod
    def criar_pedido(cliente_id: int, itens_data: List[Dict]) -> Tuple[bool, str, Optional[Pedido]]:
        """
        Cria um novo pedido com seus itens
        
        Args:
            cliente_id: ID do cliente
            itens_data: Lista de dicionários com dados dos itens
            
        Returns:
            Tuple[bool, str, Optional[Pedido]]: (sucesso, mensagem, pedido)
        """
        try:
            # Validações
            if not cliente_id:
                return False, "Cliente é obrigatório", None
            
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                return False, "Cliente não encontrado", None
            
            if not itens_data:
                return False, "Pedido deve ter pelo menos um item", None
            
            # Criar pedido
            pedido = Pedido(cliente_id=cliente_id)
            db.session.add(pedido)
            db.session.flush()  # Para obter o ID do pedido
            
            # Processar itens
            itens_validos = 0
            for item_data in itens_data:
                produto_id = item_data.get('produto_id')
                quantidade = item_data.get('quantidade')
                preco_venda = item_data.get('preco_venda')
                
                try:
                    produto_id = int(produto_id)
                    quantidade = int(quantidade)
                    preco_venda = float(preco_venda)
                except (ValueError, TypeError):
                    continue
                
                if produto_id > 0 and quantidade > 0:
                    produto = Produto.query.get(produto_id)
                    if produto:
                        # Usar o preço médio de compra do produto
                        preco_compra = float(produto.preco_medio_compra or 0)
                        valor_total_venda = quantidade * preco_venda
                        valor_total_compra = quantidade * preco_compra
                        lucro_bruto = valor_total_venda - valor_total_compra
                        
                        item = ItemPedido(
                            pedido_id=pedido.id,
                            produto_id=produto.id,
                            quantidade=quantidade,
                            preco_venda=preco_venda,
                            preco_compra=preco_compra,
                            valor_total_venda=valor_total_venda,
                            valor_total_compra=valor_total_compra,
                            lucro_bruto=lucro_bruto
                        )
                        db.session.add(item)
                        itens_validos += 1
            
            if itens_validos == 0:
                db.session.rollback()
                return False, "Nenhum item válido foi adicionado ao pedido", None
            
            db.session.commit()
            
            # Registrar atividade
            total_pedido = sum(i.valor_total_venda for i in pedido.itens)
            PedidoService._registrar_atividade(
                tipo_atividade="Criação de Pedido",
                titulo="Pedido Criado",
                descricao=f"Pedido #{pedido.id} - Cliente: {cliente.nome} - Total: R$ {total_pedido:.2f}",
                modulo="Pedidos",
                dados_extras={"pedido_id": pedido.id, "cliente_id": cliente_id, "total": total_pedido}
            )
            
            current_app.logger.info(f"Pedido criado: #{pedido.id} - Cliente: {cliente.nome} - Total: R$ {total_pedido:.2f}")
            
            return True, f"Pedido #{pedido.id} criado com sucesso", pedido
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar pedido: {str(e)}")
            return False, f"Erro ao criar pedido: {str(e)}", None
    
    @staticmethod
    def editar_pedido(pedido_id: int, cliente_id: int, itens_data: List[Dict]) -> Tuple[bool, str, Optional[Pedido]]:
        """
        Edita um pedido existente
        
        Args:
            pedido_id: ID do pedido
            cliente_id: ID do cliente
            itens_data: Lista de dicionários com dados dos itens
            
        Returns:
            Tuple[bool, str, Optional[Pedido]]: (sucesso, mensagem, pedido)
        """
        try:
            # Buscar pedido
            pedido = Pedido.query.get(pedido_id)
            if not pedido:
                return False, "Pedido não encontrado", None
            
            # Verificar se cliente existe
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                return False, "Cliente não encontrado", None
            
            if not itens_data:
                return False, "Pedido deve ter pelo menos um item", None
            
            # Atualizar cliente se necessário
            if pedido.cliente_id != cliente_id:
                pedido.cliente_id = cliente_id
            
            # Remover itens existentes
            for item in pedido.itens:
                db.session.delete(item)
            
            # Adicionar novos itens
            itens_validos = 0
            for item_data in itens_data:
                produto_id = item_data.get('produto_id')
                quantidade = item_data.get('quantidade')
                preco_venda = item_data.get('preco_venda')
                
                try:
                    produto_id = int(produto_id)
                    quantidade = int(quantidade)
                    preco_venda = float(preco_venda)
                except (ValueError, TypeError):
                    continue
                
                if produto_id > 0 and quantidade > 0:
                    produto = Produto.query.get(produto_id)
                    if produto:
                        # Usar o preço médio de compra do produto
                        preco_compra = float(produto.preco_medio_compra or 0)
                        valor_total_venda = quantidade * preco_venda
                        valor_total_compra = quantidade * preco_compra
                        lucro_bruto = valor_total_venda - valor_total_compra
                        
                        item = ItemPedido(
                            pedido_id=pedido.id,
                            produto_id=produto.id,
                            quantidade=quantidade,
                            preco_venda=preco_venda,
                            preco_compra=preco_compra,
                            valor_total_venda=valor_total_venda,
                            valor_total_compra=valor_total_compra,
                            lucro_bruto=lucro_bruto
                        )
                        db.session.add(item)
                        itens_validos += 1
            
            if itens_validos == 0:
                db.session.rollback()
                return False, "Nenhum item válido foi adicionado ao pedido", None
            
            db.session.commit()
            
            # Registrar atividade
            total_pedido = sum(i.valor_total_venda for i in pedido.itens)
            PedidoService._registrar_atividade(
                tipo_atividade="Edição de Pedido",
                titulo="Pedido Editado",
                descricao=f"Pedido #{pedido.id} - Cliente: {cliente.nome} - Total: R$ {total_pedido:.2f}",
                modulo="Pedidos",
                dados_extras={"pedido_id": pedido.id, "cliente_id": cliente_id, "total": total_pedido}
            )
            
            current_app.logger.info(f"Pedido editado: #{pedido.id} - Cliente: {cliente.nome} - Total: R$ {total_pedido:.2f}")
            
            return True, f"Pedido #{pedido.id} editado com sucesso", pedido
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao editar pedido: {str(e)}")
            return False, f"Erro ao editar pedido: {str(e)}", None
    
    @staticmethod
    def excluir_pedido(pedido_id: int) -> Tuple[bool, str]:
        """
        Exclui um pedido e todos os dados relacionados
        
        Args:
            pedido_id: ID do pedido
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            pedido = Pedido.query.get(pedido_id)
            if not pedido:
                return False, "Pedido não encontrado"
            
            # Registrar atividade antes de excluir
            cliente = Cliente.query.get(pedido.cliente_id)
            total_pedido = sum(i.valor_total_venda for i in pedido.itens)
            PedidoService._registrar_atividade(
                tipo_atividade="Exclusão de Pedido",
                titulo="Pedido Excluído",
                descricao=f"Pedido #{pedido.id} foi excluído permanentemente. Valor: R$ {total_pedido:.2f}",
                modulo="Pedidos",
                dados_extras={"pedido_id": pedido.id, "cliente_id": pedido.cliente_id, "total": total_pedido}
            )
            
            # Excluir itens do pedido
            for item in pedido.itens:
                db.session.delete(item)
            
            # Excluir pagamentos relacionados
            for pagamento in pedido.pagamentos:
                db.session.delete(pagamento)
            
            # Excluir coletas relacionadas
            coletas = Coleta.query.filter_by(pedido_id=pedido.id).all()
            for coleta in coletas:
                itens_coleta = ItemColetado.query.filter_by(coleta_id=coleta.id).all()
                for item_coleta in itens_coleta:
                    db.session.delete(item_coleta)
                db.session.delete(coleta)
            
            # Excluir pedido
            db.session.delete(pedido)
            db.session.commit()
            
            current_app.logger.info(f"Pedido excluído: #{pedido_id} - Cliente: {cliente.nome if cliente else 'N/A'}")
            
            return True, f"Pedido #{pedido_id} excluído com sucesso"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao excluir pedido: {str(e)}")
            return False, f"Erro ao excluir pedido: {str(e)}"
    
    @staticmethod
    def confirmar_pedido_comercial(pedido_id: int, senha_admin: str) -> Tuple[bool, str]:
        """
        Confirma um pedido pelo comercial
        
        Args:
            pedido_id: ID do pedido
            senha_admin: Senha do administrador
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Verificar senha do administrador
            admin = Usuario.query.filter_by(tipo='admin').first()
            if not admin or not admin.check_senha(senha_admin):
                return False, "Senha incorreta"
            
            # Buscar pedido
            pedido = Pedido.query.get(pedido_id)
            if not pedido:
                return False, "Pedido não encontrado"
            
            # Confirmar pedido
            pedido.confirmado_comercial = True
            pedido.confirmado_por = session.get('usuario_nome', 'Usuário')
            pedido.data_confirmacao = datetime.utcnow()
            
            db.session.commit()
            
            # Registrar atividade
            PedidoService._registrar_atividade(
                tipo_atividade='Confirmação Comercial',
                titulo=f'Pedido #{pedido.id} confirmado pelo comercial',
                descricao=f'Pedido do cliente {pedido.cliente.nome} foi confirmado pelo comercial e liberado para análise financeira.',
                modulo='Pedidos',
                dados_extras={"pedido_id": pedido.id, "confirmado_por": pedido.confirmado_por}
            )
            
            current_app.logger.info(f"Pedido confirmado comercialmente: #{pedido.id} por {pedido.confirmado_por}")
            
            return True, "Pedido confirmado com sucesso!"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao confirmar pedido comercial: {str(e)}")
            return False, f"Erro ao confirmar pedido: {str(e)}"
    
    @staticmethod
    def listar_pedidos(filtro_status: str = 'todos', data_inicio: str = None, data_fim: str = None, 
                       ordenar_por: str = 'data', direcao: str = 'desc') -> List[Dict]:
        """
        Lista pedidos com filtros e ordenação completa
        
        Args:
            filtro_status: Filtro por status
            data_inicio: Data de início (YYYY-MM-DD)
            data_fim: Data de fim (YYYY-MM-DD)
            ordenar_por: Campo para ordenação (id, cliente, data, valor, status)
            direcao: Direção da ordenação (asc, desc)
            
        Returns:
            List[Dict]: Lista de pedidos com informações calculadas e ordenadas
        """
        try:
            pedidos_query = Pedido.query
            
            # Filtro por data
            if data_inicio:
                try:
                    data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
                    pedidos_query = pedidos_query.filter(Pedido.data >= data_inicio_dt)
                except ValueError:
                    current_app.logger.warning(f"Data de início inválida: {data_inicio}")
            if data_fim:
                try:
                    data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1) - timedelta(seconds=1)
                    pedidos_query = pedidos_query.filter(Pedido.data <= data_fim_dt)
                except ValueError:
                    current_app.logger.warning(f"Data de fim inválida: {data_fim}")
            
            # Usar eager loading para evitar N+1 queries
            pedidos = pedidos_query.options(
                db.joinedload(Pedido.cliente),
                db.joinedload(Pedido.itens).joinedload(ItemPedido.produto),
                db.joinedload(Pedido.pagamentos)
            ).all()
            
            resultado = []
            
            # Processar todos os pedidos e calcular campos
            for pedido in pedidos:
                total_venda = sum(i.valor_total_venda for i in pedido.itens)
                total_pago = sum(p.valor for p in pedido.pagamentos)
                
                # Determinar status baseado na confirmação comercial e pagamentos
                if not pedido.confirmado_comercial:
                    status = 'Aguardando Comercial'
                elif total_pago >= total_venda and total_venda > 0:
                    status = 'LIBERADO P/ FINANCEIRO'
                else:
                    status = 'Pendente'
                
                # Aplicar filtro de status
                if filtro_status != 'todos':
                    if filtro_status == 'aguardando comercial' and status != 'Aguardando Comercial':
                        continue
                    elif filtro_status == 'liberado p/ financeiro' and status != 'LIBERADO P/ FINANCEIRO':
                        continue
                    elif filtro_status == 'pendente' and status != 'Pendente':
                        continue
                
                resultado.append({
                    'pedido': pedido,
                    'total_venda': float(total_venda),
                    'total_pago': float(total_pago),
                    'status': status,
                    'cliente_nome': pedido.cliente.nome,
                    'data_pedido': pedido.data,
                    'id_pedido': pedido.id
                })
            
            # ORDENAÇÃO EM PYTHON - 100% FUNCIONAL
            if ordenar_por == 'id':
                resultado.sort(key=lambda x: x['id_pedido'], reverse=(direcao == 'desc'))
            elif ordenar_por == 'cliente':
                resultado.sort(key=lambda x: x['cliente_nome'].lower(), reverse=(direcao == 'desc'))
            elif ordenar_por == 'data':
                resultado.sort(key=lambda x: x['data_pedido'], reverse=(direcao == 'desc'))
            elif ordenar_por == 'valor':
                resultado.sort(key=lambda x: x['total_venda'], reverse=(direcao == 'desc'))
            elif ordenar_por == 'status':
                # Ordenação por status com prioridade
                status_order = {
                    'Aguardando Comercial': 1,
                    'Pendente': 2,
                    'LIBERADO P/ FINANCEIRO': 3
                }
                resultado.sort(key=lambda x: status_order.get(x['status'], 999), reverse=(direcao == 'desc'))
            
            return resultado
            
        except Exception as e:
            current_app.logger.error(f"Erro ao listar pedidos: {str(e)}")
            return []
    
    @staticmethod
    def buscar_pedido(pedido_id: int) -> Optional[Pedido]:
        """
        Busca um pedido por ID
        
        Args:
            pedido_id: ID do pedido
            
        Returns:
            Optional[Pedido]: Pedido encontrado ou None
        """
        try:
            return Pedido.query.get(pedido_id)
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar pedido: {str(e)}")
            return None
    
    @staticmethod
    def calcular_totais_pedido(pedido_id: int) -> Dict[str, float]:
        """
        Calcula totais de um pedido
        
        Args:
            pedido_id: ID do pedido
            
        Returns:
            Dict[str, float]: Dicionário com totais
        """
        try:
            pedido = Pedido.query.get(pedido_id)
            if not pedido:
                return {'total': 0, 'pago': 0, 'saldo': 0}
            
            total = sum(i.valor_total_venda for i in pedido.itens)
            pago = sum(p.valor for p in pedido.pagamentos)
            saldo = total - pago
            
            return {
                'total': float(total),
                'pago': float(pago),
                'saldo': float(saldo)
            }
        except Exception as e:
            current_app.logger.error(f"Erro ao calcular totais do pedido: {str(e)}")
            return {'total': 0, 'pago': 0, 'saldo': 0}
    
    @staticmethod
    def calcular_necessidade_compra() -> List[Dict]:
        """
        Calcula a necessidade de compra baseada nos pedidos pagos e em coleta
        
        Returns:
            List[Dict]: Lista com produtos e necessidade de compra
        """
        try:
            from sqlalchemy import func
            from ..models import Estoque

            pedidos_liberados = (
                db.session.query(
                    Produto.id.label('produto_id'),
                    Produto.nome.label('produto_nome'),
                    func.sum(ItemPedido.quantidade).label('quantidade_pedida'),
                    func.sum(ItemPedido.valor_total_compra).label('valor_total_compra'),
                )
                .join(ItemPedido, ItemPedido.produto_id == Produto.id)
                .join(Pedido, Pedido.id == ItemPedido.pedido_id)
                .filter(
                    Pedido.status.in_([
                        StatusPedido.PAGAMENTO_APROVADO,
                        StatusPedido.COLETA_PARCIAL,
                        StatusPedido.COLETA_CONCLUIDA
                    ])
                )
                .group_by(Produto.id, Produto.nome)
                .all()
            )

            resultado: List[Dict] = []

            for row in pedidos_liberados:
                quantidade_pedida = int(row.quantidade_pedida or 0)
                if quantidade_pedida <= 0:
                    continue

                estoque = Estoque.query.filter_by(produto_id=row.produto_id).first()
                quantidade_estoque = estoque.quantidade if estoque else 0

                saldo = quantidade_estoque - quantidade_pedida
                necessidade_compra = abs(saldo) if saldo < 0 else 0

                valor_total_compra = float(row.valor_total_compra or 0)
                valor_compra_unitario = (
                    valor_total_compra / quantidade_pedida if quantidade_pedida > 0 else 0.0
                )
                valor_total_necessidade = necessidade_compra * valor_compra_unitario

                resultado.append({
                    'produto_id': row.produto_id,
                    'produto_nome': row.produto_nome,
                    'quantidade_pedida': quantidade_pedida,
                    'quantidade_estoque': quantidade_estoque,
                    'saldo': saldo,
                    'necessidade_compra': necessidade_compra,
                    'valor_compra': valor_compra_unitario,
                    'valor_total_necessidade': valor_total_necessidade,
                    'status': 'CRÍTICO' if saldo < 0 else 'SUFICIENTE' if saldo > 0 else 'ZERADO'
                })

            resultado.sort(key=lambda x: (x['necessidade_compra'], x['produto_nome']), reverse=True)

            return resultado
            
        except Exception as e:
            current_app.logger.error(f"Erro ao calcular necessidade de compra: {str(e)}")
            return []
    
    @staticmethod
    def verificar_senha_admin(senha: str) -> bool:
        """
        Verifica se a senha fornecida é do admin
        
        Args:
            senha: Senha a ser verificada
            
        Returns:
            bool: True se a senha estiver correta
        """
        try:
            admin = Usuario.query.filter_by(tipo='admin').first()
            return admin and admin.check_senha(senha)
        except Exception as e:
            current_app.logger.error(f"Erro ao verificar senha admin: {str(e)}")
            return False
    
    @staticmethod
    def processar_planilha_importacao(df):
        from collections import defaultdict
        from decimal import Decimal, InvalidOperation
        from datetime import datetime
        import pandas as pd
        import unicodedata

        def normalizar_nome(valor):
            if valor is None:
                return ''
            ascii_safe = unicodedata.normalize('NFKD', str(valor)).encode('ASCII', 'ignore').decode('ASCII')
            return ascii_safe.strip().lower()

        clientes_nome_map = defaultdict(list)
        clientes_fantasia_map = defaultdict(list)
        for cli in Cliente.query.all():
            clientes_nome_map[normalizar_nome(cli.nome)].append(cli)
            if cli.fantasia:
                clientes_fantasia_map[normalizar_nome(cli.fantasia)].append(cli)
        
        produtos_map = defaultdict(list)
        for prod in Produto.query.all():
            produtos_map[normalizar_nome(prod.nome)].append(prod)
        
        def preparar_dados_para_log(row_dict):
            dados_limpos = {}
            for chave, valor in row_dict.items():
                if isinstance(valor, Decimal):
                    dados_limpos[chave] = float(valor)
                elif isinstance(valor, pd.Timestamp):
                    dados_limpos[chave] = valor.strftime('%Y-%m-%d')
                elif isinstance(valor, datetime):
                    dados_limpos[chave] = valor.strftime('%Y-%m-%d')
                else:
                    dados_limpos[chave] = str(valor) if valor is not None else ''
            return dados_limpos

        resultados = []
        pedidos_para_criar = defaultdict(list)

        for index, row in df.iterrows():
            linha = index + 2  # Linha da planilha para o usuário
            erros_linha = []
            
            # Validações de campo
            cliente_nome = row.get('cliente_nome', None)
            cliente_fantasia = row.get('cliente_fantasia', None)
            produto_nome = row.get('produto_nome')
            quantidade = row.get('quantidade')
            preco_venda = row.get('preco_venda')
            data = row.get('data')
            data_normalizada = None

            cliente_nome_str = str(cliente_nome).strip() if cliente_nome is not None else ''
            cliente_fantasia_str = str(cliente_fantasia).strip() if cliente_fantasia is not None else ''

            if not cliente_nome_str and not cliente_fantasia_str:
                erros_linha.append("Informe ao menos 'cliente_nome' ou 'cliente_fantasia'.")
            if cliente_nome is not None and not cliente_nome_str:
                erros_linha.append("Coluna 'cliente_nome' está vazia.")
            if cliente_fantasia is not None and not cliente_fantasia_str:
                erros_linha.append("Coluna 'cliente_fantasia' está vazia.")
            if pd.isna(produto_nome) or not str(produto_nome).strip():
                erros_linha.append("Coluna 'produto_nome' está vazia.")
            if pd.isna(data):
                erros_linha.append("Coluna 'data' está vazia.")

            try:
                quantidade = int(Decimal(str(quantidade)))
                if quantidade <= 0:
                    erros_linha.append("Quantidade deve ser maior que zero.")
            except (ValueError, TypeError, InvalidOperation):
                erros_linha.append(f"Quantidade '{quantidade}' é inválida.")

            try:
                preco_venda = Decimal(str(preco_venda).replace(',', '.'))
                if preco_venda <= 0:
                    erros_linha.append("Preço de venda deve ser maior que zero.")
            except (ValueError, TypeError, InvalidOperation):
                erros_linha.append(f"Preço de venda '{preco_venda}' é inválido.")

            try:
                data_normalizada = pd.to_datetime(data, errors='raise', dayfirst=True).to_pydatetime()
            except ValueError:
                erros_linha.append(f"Data '{data}' é inválida. Use formato AAAA-MM-DD ou DD/MM/AAAA.")

            if erros_linha:
                resultados.append({
                    'linha': linha,
                    'status': 'Falha',
                    'erros': erros_linha,
                    'dados': preparar_dados_para_log(row.to_dict())
                })
                continue

            # Validação de Negócio
            candidatos_cliente = []
            if cliente_nome_str:
                candidatos_cliente.extend(clientes_nome_map.get(normalizar_nome(cliente_nome_str), []))
            if cliente_fantasia_str:
                candidatos_cliente.extend(clientes_fantasia_map.get(normalizar_nome(cliente_fantasia_str), []))

            clientes_unicos = list({cli.id: cli for cli in candidatos_cliente}.values())

            if not clientes_unicos:
                if cliente_fantasia_str and not cliente_nome_str:
                    erros_linha.append(f"Cliente com fantasia '{cliente_fantasia_str}' não encontrado.")
                elif cliente_nome_str and not cliente_fantasia_str:
                    erros_linha.append(f"Cliente '{cliente_nome_str}' não encontrado.")
                else:
                    erros_linha.append(
                        f"Cliente não encontrado (nome: '{cliente_nome_str}' | fantasia: '{cliente_fantasia_str}')."
                    )
            elif len(clientes_unicos) > 1:
                ids = ', '.join(str(cli.id) for cli in clientes_unicos[:5])
                if len(clientes_unicos) > 5:
                    ids += ', ...'
                erros_linha.append(f"Mais de um cliente encontrado para os dados informados (IDs: {ids}).")
            else:
                cliente = clientes_unicos[0]

            produto_lista = produtos_map.get(normalizar_nome(produto_nome), [])
            if not produto_lista:
                erros_linha.append(f"Produto '{produto_nome}' não encontrado.")
            elif len(produto_lista) > 1:
                ids = ', '.join(str(prod.id) for prod in produto_lista[:5])
                if len(produto_lista) > 5:
                    ids += ', ...'
                erros_linha.append(
                    f"Produto '{produto_nome}' não é único. Ajuste o nome cadastrado ou use um apelido único (IDs: {ids})."
                )
            else:
                produto = produto_lista[0]

            if erros_linha:
                resultados.append({
                    'linha': linha,
                    'status': 'Falha',
                    'erros': erros_linha,
                    'dados': preparar_dados_para_log(row.to_dict())
                })
                continue
            dados_linha = preparar_dados_para_log(row.to_dict())
            
            # Agrupamento para criação de pedido
            chave_pedido = (cliente.id, data_normalizada.date())
            pedidos_para_criar[chave_pedido].append({
                'produto': produto,
                'quantidade': quantidade,
                'preco_venda': preco_venda
            })
            resultados.append({'linha': linha, 'status': 'Sucesso', 'erros': [], 'dados': dados_linha})

        # Se houver linhas válidas, criar os pedidos
        pedidos_criados = 0
        if any(r['status'] == 'Sucesso' for r in resultados):
            try:
                for (cliente_id, data_pedido), itens_data in pedidos_para_criar.items():
                    datetime_pedido = datetime.combine(data_pedido, datetime.min.time())
                    novo_pedido = Pedido(cliente_id=cliente_id, data=datetime_pedido)
                    db.session.add(novo_pedido)
                    db.session.flush() # Obter ID do pedido

                    for item_data in itens_data:
                        produto = item_data['produto']
                        preco_compra = produto.preco_medio_compra or Decimal(0)
                        item = ItemPedido(
                            pedido_id=novo_pedido.id,
                            produto_id=produto.id,
                            quantidade=item_data['quantidade'],
                            preco_venda=item_data['preco_venda'],
                            preco_compra=preco_compra,
                            valor_total_venda=item_data['quantidade'] * item_data['preco_venda'],
                            valor_total_compra=item_data['quantidade'] * preco_compra,
                            lucro_bruto=(item_data['quantidade'] * item_data['preco_venda']) - (item_data['quantidade'] * preco_compra)
                        )
                        db.session.add(item)
                    pedidos_criados += 1
                db.session.commit()
                
                if pedidos_criados > 0:
                    PedidoService._registrar_atividade(
                        'importacao',
                        'Importação de pedidos históricos',
                        f'{pedidos_criados} pedido(s) importado(s) via planilha',
                        'pedidos',
                        {'pedidos_importados': pedidos_criados}
                    )

            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Erro ao salvar pedidos importados no banco: {e}")
                # Adicionar um erro geral a todos os resultados que eram de sucesso
                for r in resultados:
                    if r['status'] == 'Sucesso':
                        r['status'] = 'Falha'
                        r['erros'].append("Erro interno no banco de dados ao salvar o pedido.")
                pedidos_criados = 0

        return {
            'resumo': {
                'total_linhas': len(df),
                'sucesso': len([r for r in resultados if r['status'] == 'Sucesso']),
                'falha': len([r for r in resultados if r['status'] == 'Falha']),
                'pedidos_criados': pedidos_criados
            },
            'resultados': [r for r in resultados if r['status'] == 'Falha'] # Retornar apenas as linhas com falha
        }

    @staticmethod
    def _registrar_atividade(tipo_atividade: str, titulo: str, descricao: str, modulo: str, dados_extras: Dict = None) -> None:
        """
        Registra atividade no log do sistema
        
        Args:
            tipo_atividade: Tipo da atividade
            titulo: Título da atividade
            descricao: Descrição da atividade
            modulo: Módulo onde ocorreu
            dados_extras: Dados extras para o log
        """
        try:
            from ..models import LogAtividade
            if 'usuario_id' in session:
                # Converter valores Decimal para float antes da serialização JSON
                if dados_extras:
                    dados_convertidos = {}
                    for key, value in dados_extras.items():
                        if hasattr(value, '__class__') and value.__class__.__name__ == 'Decimal':
                            dados_convertidos[key] = float(value)
                        else:
                            dados_convertidos[key] = value
                    dados_json = json.dumps(dados_convertidos)
                else:
                    dados_json = None
                
                log = LogAtividade(
                    usuario_id=session['usuario_id'],
                    tipo_atividade=tipo_atividade,
                    titulo=titulo,
                    descricao=descricao,
                    modulo=modulo,
                    dados_extras=dados_json
                )
                db.session.add(log)
                db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Erro ao registrar atividade: {e}")
            # Não falhar se o log não puder ser registrado
            pass
