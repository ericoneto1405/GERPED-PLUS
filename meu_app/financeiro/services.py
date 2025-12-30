"""
Serviços para o módulo de financeiro
Contém toda a lógica de negócio separada das rotas
"""
import calendar
import hashlib
import mimetypes
import os
import shutil
import json
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from uuid import uuid4

from flask import current_app
from sqlalchemy.orm import joinedload
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import SQLAlchemyError

from ..models import db, Pedido, Pagamento, StatusPedido, PagamentoAnexo, CarteiraCredito
from ..time_utils import local_now, utcnow
from .config import FinanceiroConfig
from .exceptions import (
    FinanceiroValidationError, 
    PagamentoDuplicadoError, 
    PedidoNaoEncontradoError,
    ValorInvalidoError,
    ComprovanteObrigatorioError
)

class FinanceiroService:
    """Serviço para operações relacionadas ao financeiro"""
    
    _anexo_table_ready = False

    @staticmethod
    def _ensure_pagamento_anexo_table() -> bool:
        if FinanceiroService._anexo_table_ready:
            return True
        try:
            bind = db.session.get_bind()
            inspector = sa_inspect(bind)
            if not inspector.has_table('pagamento_anexo'):
                PagamentoAnexo.__table__.create(bind, checkfirst=True)
            FinanceiroService._anexo_table_ready = True
            return True
        except Exception as exc:
            current_app.logger.warning(f"Não foi possível garantir tabela pagamento_anexo: {exc}")
            return False
    
    @staticmethod
    def _supports_pagamento_anexo_table() -> bool:
        return FinanceiroService._ensure_pagamento_anexo_table()
    
    @staticmethod
    def _get_date_range(mes: str, ano: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Calcula o range de datas para filtros de mês e ano
        
        Args:
            mes: Mês como string (1-12)
            ano: Ano como string
            
        Returns:
            Tuple[Optional[datetime], Optional[datetime]]: (data_inicio, data_fim)
        """
        if not mes and not ano:
            return None, None
            
        if mes and ano:
            # Filtro por mês e ano específicos
            ano_int = int(ano)
            mes_int = int(mes)
            data_inicio = datetime(ano_int, mes_int, 1)
            # Usar calendar.monthrange para obter o último dia do mês
            ultimo_dia = calendar.monthrange(ano_int, mes_int)[1]
            data_fim = datetime(ano_int, mes_int, ultimo_dia, 23, 59, 59)
            return data_inicio, data_fim
            
        elif ano:
            # Filtro apenas por ano
            ano_int = int(ano)
            data_inicio = datetime(ano_int, 1, 1)
            data_fim = datetime(ano_int, 12, 31, 23, 59, 59)
            return data_inicio, data_fim
            
        elif mes:
            # Filtro apenas por mês (ano atual)
            ano_atual = local_now().year
            mes_int = int(mes)
            data_inicio = datetime(ano_atual, mes_int, 1)
            ultimo_dia = calendar.monthrange(ano_atual, mes_int)[1]
            data_fim = datetime(ano_atual, mes_int, ultimo_dia, 23, 59, 59)
            return data_inicio, data_fim
            
        return None, None
    
    @staticmethod
    def listar_pedidos_financeiro(
        tipo_filtro: str = 'pendentes',
        mes: str = '',
        ano: str = '',
        ordenar_por: str = 'data',
        direcao: str = 'desc'
    ) -> List[Dict]:
        """
        Lista pedidos para análise financeira
        
        Args:
            tipo_filtro: Tipo de filtro (pendentes, pagos, etc.)
            mes: Mês para filtrar
            ano: Ano para filtrar
            
        Returns:
            List[Dict]: Lista de pedidos com informações financeiras ordenados
        """
        try:
            # IMPORTANTE: O módulo financeiro só deve mostrar pedidos confirmados pelo comercial
            pedidos_query = Pedido.query.filter(Pedido.confirmado_comercial == True)
            
            # Aplicar filtros de data usando função helper
            data_inicio, data_fim = FinanceiroService._get_date_range(mes, ano)
            if data_inicio and data_fim:
                pedidos_query = pedidos_query.filter(Pedido.data >= data_inicio, Pedido.data <= data_fim)
            
            # Otimização: Carregar relacionamentos de uma vez para evitar N+1 queries
            pedidos = pedidos_query.options(
                joinedload(Pedido.itens),
                joinedload(Pedido.pagamentos)
            ).order_by(Pedido.data.desc()).all()
            
            resultado = []

            filtro_status = (tipo_filtro or 'todos').lower()

            for pedido in pedidos:
                totais = pedido.calcular_totais()
                total_pedido = totais['total_pedido']
                total_pago = totais['total_pago']
                saldo = max(total_pedido - total_pago, 0)

                if total_pago <= 0:
                    status_financeiro = 'AGUARDANDO'
                elif total_pago < total_pedido:
                    status_financeiro = 'PAGO PARCIAL'
                else:
                    status_financeiro = 'PAGO'

                deve_incluir = (
                    filtro_status == 'todos' or
                    (filtro_status == 'pendentes' and status_financeiro in ('AGUARDANDO', 'PAGO PARCIAL')) or
                    (filtro_status == 'pagos' and status_financeiro == 'PAGO')
                )

                if deve_incluir:
                    resultado.append({
                        'pedido': pedido,
                        'total_pedido': total_pedido,
                        'total_pago': total_pago,
                        'saldo': saldo,
                        'status': status_financeiro
                    })
            
            reverse = (direcao == 'desc')
            if ordenar_por == 'id':
                resultado.sort(key=lambda x: x['pedido'].id, reverse=reverse)
            elif ordenar_por == 'cliente':
                resultado.sort(key=lambda x: x['pedido'].cliente.nome.lower(), reverse=reverse)
            elif ordenar_por == 'data':
                resultado.sort(key=lambda x: x['pedido'].data, reverse=reverse)
            elif ordenar_por == 'status':
                status_order = {'AGUARDANDO': 1, 'PAGO PARCIAL': 2, 'PAGO': 3}
                resultado.sort(key=lambda x: status_order.get(x['status'], 999), reverse=reverse)
            elif ordenar_por == 'valor':
                resultado.sort(key=lambda x: x['total_pedido'], reverse=reverse)
            elif ordenar_por == 'pago':
                resultado.sort(key=lambda x: x['total_pago'], reverse=reverse)
            elif ordenar_por == 'saldo':
                resultado.sort(key=lambda x: x['saldo'], reverse=reverse)

            return resultado
            
        except Exception as e:
            current_app.logger.error(f"Erro ao listar pedidos financeiro: {str(e)}")
            return []
    
    @staticmethod
    def registrar_pagamento(
        pedido_id: int, 
        valor: float, 
        forma_pagamento: str, 
        observacoes: str = '', 
        caminho_recibo: str = None, 
        id_transacao: str = None, 
        recibo_mime: Optional[str] = None, 
        recibo_tamanho: Optional[int] = None, 
        recibo_sha256: Optional[str] = None,
        anexos_detalhes: Optional[List[dict]] = None,
        # NOVOS PARÂMETROS - dados extraídos do comprovante
        data_comprovante: Optional[str] = None,
        banco_emitente: Optional[str] = None,
        agencia_recebedor: Optional[str] = None,
        conta_recebedor: Optional[str] = None,
        chave_pix_recebedor: Optional[str] = None,
        comprovante_compartilhado_origem_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[Pagamento]]:
        """
        Registra um pagamento com dados completos extraídos do comprovante.
        """
        try:
            # Validações com exceções específicas
            if not pedido_id:
                raise FinanceiroValidationError("Pedido é obrigatório")
            
            pedido = Pedido.query.get(pedido_id)
            if not pedido:
                raise PedidoNaoEncontradoError(f"Pedido {pedido_id} não encontrado")
            
            if valor <= 0:
                raise ValorInvalidoError(f"Valor deve ser maior que zero. Valor fornecido: {valor}")
            
            if not forma_pagamento or not forma_pagamento.strip():
                raise FinanceiroValidationError("Forma de pagamento é obrigatória")

            # Validação para PIX: comprovante é obrigatório (usando configuração)
            if FinanceiroConfig.is_pix_payment_requiring_receipt() and 'pix' in forma_pagamento.lower() and not caminho_recibo:
                raise ComprovanteObrigatorioError("Para pagamentos com PIX, o envio do comprovante é obrigatório.")

            # VERIFICAÇÃO DE DUPLICIDADE PELO ID DA TRANSAÇÃO
            if id_transacao and id_transacao.strip():
                id_transacao_limpo = id_transacao.strip()
                pagamento_existente = Pagamento.query.filter_by(id_transacao=id_transacao_limpo).first()
                if pagamento_existente:
                    mensagem_erro = f"Este recibo (ID: {id_transacao_limpo}) já foi utilizado no pagamento do pedido #{pagamento_existente.pedido_id} em {pagamento_existente.data_pagamento.strftime('%d/%m/%Y')}."
                    current_app.logger.warning(mensagem_erro)
                    raise PagamentoDuplicadoError(mensagem_erro)
            else:
                id_transacao_limpo = None

            # Converter valor para Decimal para consistência com o banco
            valor_decimal = Decimal(str(valor))

            # Verificar se o novo pagamento ultrapassa o total do pedido
            totais_atuais = pedido.calcular_totais()
            total_pedido_decimal = Decimal(str(totais_atuais['total_pedido']))
            total_pago_decimal = Decimal(str(totais_atuais['total_pago']))
            saldo_restante = total_pedido_decimal - total_pago_decimal
            if saldo_restante < Decimal('0'):
                saldo_restante = Decimal('0')

            if saldo_restante == Decimal('0'):
                raise FinanceiroValidationError(
                    "O valor somado dos comprovantes é maior do que o pedido. Verifique com o Admin."
                )

            if valor_decimal > saldo_restante:
                raise FinanceiroValidationError(
                    "O valor somado dos comprovantes é maior do que o pedido. Verifique com o Admin."
                )
            
            # Processar data do comprovante se fornecida
            data_comprovante_parsed = None
            if data_comprovante:
                try:
                    # Tentar diferentes formatos de data
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d']:
                        try:
                            data_comprovante_parsed = datetime.strptime(data_comprovante, fmt).date()
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    current_app.logger.warning(f"Erro ao processar data do comprovante '{data_comprovante}': {e}")
            
            # Criar pagamento com todos os dados
            novo_pagamento = Pagamento(
                pedido_id=pedido_id,
                valor=valor_decimal,
                metodo_pagamento=forma_pagamento.strip(),
                observacoes=observacoes.strip() if observacoes else None,
                caminho_recibo=caminho_recibo,
                id_transacao=id_transacao_limpo,
                recibo_mime=recibo_mime,
                recibo_tamanho=recibo_tamanho,
                recibo_sha256=recibo_sha256,
                # NOVOS CAMPOS - dados extraídos do comprovante
                data_comprovante=data_comprovante_parsed,
                banco_emitente=banco_emitente.strip() if banco_emitente else None,
                agencia_recebedor=agencia_recebedor.strip() if agencia_recebedor else None,
                conta_recebedor=conta_recebedor.strip() if conta_recebedor else None,
                chave_pix_recebedor=chave_pix_recebedor.strip() if chave_pix_recebedor else None,
                comprovante_compartilhado_origem_id=comprovante_compartilhado_origem_id
            )

            anexos_para_salvar = []
            if anexos_detalhes:
                anexos_para_salvar = anexos_detalhes
            elif caminho_recibo:
                anexos_para_salvar = [{
                    'caminho': caminho_recibo,
                    'mime': recibo_mime,
                    'tamanho': recibo_tamanho,
                    'sha256': recibo_sha256,
                    'principal': True
                }]

            suportar_anexos = FinanceiroService._supports_pagamento_anexo_table()
            if suportar_anexos:
                for info in anexos_para_salvar:
                    caminho = info.get('caminho')
                    if not caminho:
                        continue
                    novo_pagamento.anexos.append(
                        PagamentoAnexo(
                            caminho=caminho,
                            mime=info.get('mime'),
                            tamanho=info.get('tamanho'),
                            sha256=info.get('sha256'),
                            principal=bool(info.get('principal')),
                            valor=info.get('valor')
                        )
                    )
            else:
                extras = [info for info in anexos_para_salvar if not info.get('principal')]
                if extras:
                    try:
                        existing = json.loads(novo_pagamento.ocr_json or "{}")
                    except ValueError:
                        existing = {}
                    existing['anexos_extra'] = extras
                    novo_pagamento.ocr_json = json.dumps(existing, ensure_ascii=False)
            
            db.session.add(novo_pagamento)
            db.session.flush() # Garante que o novo pagamento esteja na sessão para o cálculo abaixo

            # CORREÇÃO CRÍTICA: Forçar atualização da coleção pagamentos
            # Após flush(), a coleção self.pagamentos não é automaticamente atualizada
            db.session.refresh(pedido)  # Força reload do objeto pedido do banco

            # Usar método centralizado do modelo - CORRIGINDO O ERRO DE TIPO
            totais = pedido.calcular_totais()

            # CORREÇÃO: Converter para Decimal antes da comparação
            total_pago_decimal = Decimal(str(totais['total_pago']))
            total_pedido_decimal = Decimal(str(totais['total_pedido']))
            
            # O status do pedido é atualizado para pago se o valor total for atingido
            if total_pago_decimal >= total_pedido_decimal:
                pedido.status = StatusPedido.PAGAMENTO_APROVADO

            db.session.commit()

            current_app.logger.info(f"Pagamento registrado: Pedido #{pedido_id} - R$ {valor:.2f} - ID Transação: {id_transacao_limpo}")
            current_app.logger.info(f"Dados extraídos - Banco: {banco_emitente}, Agência: {agencia_recebedor}, Conta: {conta_recebedor}")
            
            return True, "Pagamento registrado com sucesso", novo_pagamento
            
        except (FinanceiroValidationError, PagamentoDuplicadoError, PedidoNaoEncontradoError, 
                ValorInvalidoError, ComprovanteObrigatorioError) as e:
            db.session.rollback()
            current_app.logger.warning(f"Erro de validação no pagamento: {str(e)}")
            return False, str(e), None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro inesperado ao registrar pagamento: {str(e)}")
            return False, f"Erro interno ao registrar pagamento. Tente novamente.", None
    
    @staticmethod
    def exportar_dados_financeiro(mes: str = '', ano: str = '') -> Dict:
        """
        Exporta dados financeiros
        
        Args:
            mes: Mês para filtrar
            ano: Ano para filtrar
            
        Returns:
            Dict: Dados financeiros para exportação
        """
        try:
            pedidos = FinanceiroService.listar_pedidos_financeiro('todos', mes, ano)
            
            total_receita = sum(p['total_pedido'] for p in pedidos)
            total_recebido = sum(p['total_pago'] for p in pedidos)
            total_pendente = sum(max(0, p['saldo']) for p in pedidos)
            
            return {
                'pedidos': pedidos,
                'total_receita': total_receita,
                'total_recebido': total_recebido,
                'total_pendente': total_pendente,
                'mes': mes,
                'ano': ano
            }
            
        except Exception as e:
            current_app.logger.error(f"Erro ao exportar dados financeiros: {str(e)}")
            return {
                'pedidos': [],
                'total_receita': 0,
                'total_recebido': 0,
                'total_pendente': 0,
                'mes': mes,
                'ano': ano
            }

    # --- Compartilhamento de comprovantes ---
    @staticmethod
    def duplicar_recibo_compartilhado(caminho_relativo: str) -> Tuple[str, str, int, str]:
        """Copia um recibo existente para um novo arquivo e retorna metadados.

        Recalcula hash para deduplicação e rejeita cópias de comprovantes já utilizados.
        """
        if not caminho_relativo:
            raise FileNotFoundError('Comprovante original não encontrado')
        origem_dir = FinanceiroConfig.get_upload_directory('recibos')
        origem_path = os.path.join(origem_dir, caminho_relativo)
        if not os.path.exists(origem_path):
            raise FileNotFoundError(f'Arquivo original {caminho_relativo} não existe mais no servidor')

        novo_nome = f"compartilhado_{uuid4().hex}_{os.path.basename(caminho_relativo)}"
        destino_path = os.path.join(origem_dir, novo_nome)
        shutil.copyfile(origem_path, destino_path)

        mime_type = mimetypes.guess_type(destino_path)[0] or 'application/octet-stream'
        tamanho = os.path.getsize(destino_path)
        sha256 = FinanceiroService._calcular_sha256(destino_path)

        if not sha256:
            os.remove(destino_path)
            raise FinanceiroValidationError('Não foi possível calcular a assinatura do comprovante compartilhado.')

        anexo_existente = None
        try:
            anexo_existente = PagamentoAnexo.query.filter_by(sha256=sha256).first()
        except SQLAlchemyError as exc:
            current_app.logger.debug(f"Não foi possível verificar anexos por hash: {exc}")
        if anexo_existente or Pagamento.query.filter_by(recibo_sha256=sha256).first():
            os.remove(destino_path)
            raise PagamentoDuplicadoError('Este comprovante já foi utilizado em outro pagamento.')

        return novo_nome, mime_type, tamanho, sha256

    @staticmethod
    def _calcular_sha256(path: str) -> Optional[str]:
        try:
            hasher = hashlib.sha256()
            with open(path, 'rb') as arquivo:
                for chunk in iter(lambda: arquivo.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return None

    @staticmethod
    def disponibilizar_pagamento_para_outro_pedido(pagamento: Pagamento, usuario_nome: Optional[str] = None) -> bool:
        if not pagamento or not pagamento.caminho_recibo:
            return False
        pagamento.compartilhado_disponivel = True
        pagamento.compartilhado_por = usuario_nome or 'Sistema'
        pagamento.compartilhado_em = utcnow()
        pagamento.compartilhado_usado_em = None
        pagamento.compartilhado_destino_pedido_id = None
        try:
            db.session.commit()
            return True
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(f'Erro ao disponibilizar comprovante #{pagamento.id}: {exc}')
            return False

    @staticmethod
    def listar_comprovantes_compartilhados() -> List[Dict]:
        try:
            comprovantes = Pagamento.query.options(joinedload(Pagamento.pedido).joinedload(Pedido.cliente))\
                .filter(Pagamento.compartilhado_disponivel.is_(True))\
                .order_by(Pagamento.compartilhado_em.desc())\
                .limit(50).all()
            resultado = []
            for comp in comprovantes:
                principal = comp.anexo_principal
                caminho = principal['caminho'] if principal else comp.caminho_recibo
                resultado.append({
                    'id': comp.id,
                    'pedido_id': comp.pedido_id,
                    'cliente': comp.pedido.cliente.nome if comp.pedido and comp.pedido.cliente else 'Cliente',
                    'valor_sugerido': float(comp.valor),
                    'id_transacao': comp.id_transacao,
                    'data_pagamento': comp.data_pagamento.strftime('%d/%m/%Y %H:%M') if comp.data_pagamento else '-',
                    'data_comprovante': comp.data_comprovante.strftime('%d/%m/%Y') if comp.data_comprovante else None,
                    'compartilhado_por': comp.compartilhado_por,
                    'compartilhado_em': comp.compartilhado_em.strftime('%d/%m/%Y %H:%M') if comp.compartilhado_em else None,
                    'banco_emitente': comp.banco_emitente,
                    'caminho_recibo': caminho
                })
            return resultado
        except Exception as exc:
            current_app.logger.error(f'Erro ao listar comprovantes compartilhados: {exc}')
            return []

    @staticmethod
    def descartar_comprovante_compartilhado(pagamento_id: int) -> bool:
        if not pagamento_id:
            return False
        pagamento = Pagamento.query.get(pagamento_id)
        if not pagamento:
            return False
        pagamento.compartilhado_disponivel = False
        pagamento.compartilhado_por = None
        pagamento.compartilhado_em = None
        try:
            db.session.commit()
            return True
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(f'Erro ao descartar comprovante compartilhado #{pagamento_id}: {exc}')
            return False

    @staticmethod
    def marcar_comprovante_compartilhado_usado(pagamento: Pagamento, pedido_destino_id: int) -> None:
        if not pagamento:
            return
        pagamento.compartilhado_disponivel = False
        pagamento.compartilhado_usado_em = utcnow()
        pagamento.compartilhado_destino_pedido_id = pedido_destino_id
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(f'Erro ao marcar comprovante compartilhado #{pagamento.id} como usado: {exc}')

    @staticmethod
    def listar_creditos_cliente(cliente_id: int) -> List[Dict]:
        if not cliente_id:
            return []
        try:
            creditos = CarteiraCredito.query.filter(
                CarteiraCredito.cliente_id == cliente_id,
                CarteiraCredito.status == 'disponivel',
                CarteiraCredito.saldo_disponivel > 0
            ).order_by(CarteiraCredito.criado_em.asc()).all()
            resultado = []
            for credito in creditos:
                valor = float(credito.saldo_disponivel or 0)
                resultado.append({
                    'id': credito.id,
                    'valor': valor,
                    'valor_formatado': f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    'data': credito.criado_em.strftime('%d/%m/%Y %H:%M') if credito.criado_em else '-',
                    'pedido_origem': credito.pedido_origem_id,
                    'observacao': f"Crédito do pedido #{credito.pedido_origem_id}" if credito.pedido_origem_id else 'Crédito disponível'
                })
            return resultado
        except Exception as exc:
            current_app.logger.error(f'Erro ao listar créditos da carteira: {exc}')
            return []

    @staticmethod
    def obter_credito_disponivel(credito_id: int) -> Optional[CarteiraCredito]:
        if not credito_id:
            return None
        credito = CarteiraCredito.query.get(credito_id)
        if not credito or credito.status != 'disponivel' or not credito.saldo_disponivel or credito.saldo_disponivel <= 0:
            return None
        return credito

    @staticmethod
    def preparar_credito_para_pagamento(credito: CarteiraCredito, usuario_nome: Optional[str] = None) -> dict:
        if not credito or credito.status != 'disponivel' or credito.saldo_disponivel <= 0:
            raise FinanceiroValidationError('Crédito selecionado não está disponível.')
        origem_dir = FinanceiroConfig.get_upload_directory('recibos')
        origem_path = os.path.join(origem_dir, credito.caminho_anexo)
        if not os.path.exists(origem_path):
            raise FinanceiroValidationError('Arquivo do crédito não foi encontrado. Contate o administrador.')
        novo_nome = f"carteira_{uuid4().hex}_{os.path.basename(credito.caminho_anexo)}"
        destino_path = os.path.join(origem_dir, novo_nome)
        shutil.copyfile(origem_path, destino_path)
        sha256 = FinanceiroService._calcular_sha256(destino_path)
        if not sha256:
            os.remove(destino_path)
            raise FinanceiroValidationError('Não foi possível validar o arquivo do crédito.')
        return {
            'caminho': novo_nome,
            'mime': credito.mime,
            'tamanho': credito.tamanho,
            'sha256': sha256,
            'principal': True,
            'origem_credito_id': credito.id,
            'original_name': credito.caminho_anexo
        }

    @staticmethod
    def criar_credito_carteira(cliente_id: int, pedido_origem_id: int, pagamento: Pagamento,
                               caminho_anexo: str, valor: float, usuario_nome: Optional[str] = None,
                               original_name: Optional[str] = None) -> Optional[CarteiraCredito]:
        if not cliente_id or not pagamento or not caminho_anexo or not valor:
            return None
        try:
            anexo = next((a for a in pagamento.anexos if a.caminho == caminho_anexo), None)
        except Exception:
            anexo = None
        valor_decimal = Decimal(str(valor))
        try:
            credito = CarteiraCredito(
                cliente_id=cliente_id,
                pedido_origem_id=pedido_origem_id,
                pagamento_origem_id=pagamento.id,
                pagamento_anexo_id=anexo.id if anexo else None,
                caminho_anexo=caminho_anexo,
                mime=(anexo.mime if anexo else None),
                tamanho=(anexo.tamanho if anexo else None),
                sha256=(anexo.sha256 if anexo else None),
                valor_total=valor_decimal,
                saldo_disponivel=valor_decimal,
                criado_por=usuario_nome or 'Sistema'
            )
            db.session.add(credito)
            db.session.commit()
            current_app.logger.info(f"Crédito criado para cliente #{cliente_id} a partir do pagamento #{pagamento.id}")
            return credito
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(f'Erro ao criar crédito de carteira: {exc}')
            return None

    @staticmethod
    def consumir_credito_carteira(credito: CarteiraCredito, pedido_destino_id: int,
                                  pagamento_destino: Optional[Pagamento] = None) -> bool:
        if not credito:
            return False
        try:
            credito.pedido_destino_id = pedido_destino_id
            credito.pagamento_destino_id = pagamento_destino.id if pagamento_destino else None
            credito.saldo_disponivel = Decimal('0')
            credito.status = 'utilizado'
            credito.utilizado_em = utcnow()
            db.session.commit()
            return True
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(f'Erro ao consumir crédito #{credito.id}: {exc}')
            return False
    
