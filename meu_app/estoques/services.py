"""
Serviços para o módulo de estoques
Contém toda a lógica de negócio separada das rotas
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from flask import current_app, session

from ..models import LogAtividade, MovimentacaoEstoque, Produto, Estoque, db
from ..time_utils import now_utc

class EstoqueService:
    """Serviço para operações relacionadas a estoques"""
    
    @staticmethod
    def criar_estoque(produto_id: int, quantidade: int, data_entrada: str, conferente: str = None, status: str = 'Contagem', observacoes: str = '') -> Tuple[bool, str, Optional[Estoque]]:
        """
        Cria um novo registro de estoque (um por produto)
        
        Args:
            produto_id: ID do produto
            quantidade: Quantidade em estoque
            data_entrada: Data de entrada
            conferente: Nome do conferente
            status: Status do estoque (ENTRADA DE NF DO FORNECEDOR ou TRANSFERÊNCIA ENTRE LOJAS)
            
        Returns:
            Tuple[bool, str, Optional[Estoque]]: (sucesso, mensagem, estoque)
        """
        try:
            # Validações
            if not produto_id:
                return False, "Produto é obrigatório", None
            
            produto = Produto.query.get(produto_id)
            if not produto:
                return False, "Produto não encontrado", None
            
            if quantidade < 0:
                return False, "Quantidade não pode ser negativa", None
            
            # Verificar se já existe estoque para este produto
            estoque_existente = Estoque.query.filter_by(produto_id=produto_id).first()
            if estoque_existente:
                return False, "Já existe um registro de estoque para este produto", None
            
            # Converter data_entrada de string para datetime
            try:
                if data_entrada:
                    data_entrada_dt = datetime.fromisoformat(
                        data_entrada.replace('Z', '+00:00')
                    )
                else:
                    data_entrada_dt = now_utc()
            except ValueError:
                data_entrada_dt = now_utc()
            
            # Usar nome do usuário logado como conferente se não fornecido
            if not conferente:
                conferente = session.get('usuario_nome', 'Sistema')
            
            # Criar estoque
            novo_estoque = Estoque(
                produto_id=produto_id,
                quantidade=quantidade,
                data_entrada=data_entrada_dt,
                conferente=conferente,
                status=status
            )
            
            db.session.add(novo_estoque)
            db.session.commit()
            
            # Registrar movimentação inicial
            EstoqueService._registrar_movimentacao(
                produto_id=produto_id,
                tipo_movimentacao="Entrada",
                quantidade_anterior=0,
                quantidade_movimentada=quantidade,
                quantidade_atual=quantidade,
                motivo="Criação inicial do estoque",
                responsavel=conferente,
                observacoes=observacoes
            )
            
            # Registrar atividade
            EstoqueService._registrar_atividade(
                tipo_atividade="Criação de Estoque",
                titulo="Estoque Criado",
                descricao=f"Estoque: {produto.nome} - Qtd: {quantidade}",
                modulo="Estoques",
                dados_extras={"estoque_id": novo_estoque.id, "produto_id": produto_id, "quantidade": quantidade}
            )
            
            current_app.logger.info(f"Estoque criado: {produto.nome} (ID: {novo_estoque.id})")
            
            return True, "Estoque criado com sucesso", novo_estoque
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar estoque: {str(e)}")
            return False, f"Erro ao criar estoque: {str(e)}", None
    
    @staticmethod
    def editar_estoque(estoque_id: int, quantidade: int, data_entrada: str, status: str = None, observacoes: str = '') -> Tuple[bool, str, Optional[Estoque]]:
        """
        Edita um registro de estoque
        
        Args:
            estoque_id: ID do estoque
            quantidade: Nova quantidade
            data_entrada: Nova data de entrada
            status: Novo status do estoque
            
        Returns:
            Tuple[bool, str, Optional[Estoque]]: (sucesso, mensagem, estoque)
        """
        try:
            # Buscar estoque
            estoque = Estoque.query.get(estoque_id)
            if not estoque:
                return False, "Estoque não encontrado", None
            
            # Validações
            if quantidade < 0:
                return False, "Quantidade não pode ser negativa", None
            
            # Guardar quantidade anterior para movimentação
            quantidade_anterior = estoque.quantidade
            
            # Converter data_entrada de string para datetime
            try:
                if data_entrada:
                    data_entrada_dt = datetime.fromisoformat(
                        data_entrada.replace('Z', '+00:00')
                    )
                else:
                data_entrada_dt = now_utc()
            except ValueError:
                data_entrada_dt = now_utc()
            
            # Atualizar dados
            estoque.quantidade = quantidade
            estoque.data_entrada = data_entrada_dt
            if status:
                estoque.status = status
            
            db.session.commit()
            
            # Registrar movimentação se houve mudança na quantidade
            if quantidade_anterior != quantidade:
                tipo_movimentacao = "Entrada" if quantidade > quantidade_anterior else "Saída"
                quantidade_movimentada = abs(quantidade - quantidade_anterior)
                
                EstoqueService._registrar_movimentacao(
                    produto_id=estoque.produto_id,
                    tipo_movimentacao=tipo_movimentacao,
                    quantidade_anterior=quantidade_anterior,
                    quantidade_movimentada=quantidade_movimentada,
                    quantidade_atual=quantidade,
                    motivo="Ajuste manual de estoque",
                    responsavel=session.get('usuario_nome', 'Sistema'),
                    observacoes=observacoes
                )
            
            # Registrar atividade
            EstoqueService._registrar_atividade(
                tipo_atividade="Edição de Estoque",
                titulo="Estoque Editado",
                descricao=f"Estoque editado: {estoque.produto.nome} - Qtd: {quantidade}",
                modulo="Estoques",
                dados_extras={"estoque_id": estoque.id, "produto_id": estoque.produto_id, "quantidade": quantidade}
            )
            
            current_app.logger.info(f"Estoque editado: {estoque.produto.nome} (ID: {estoque.id})")
            
            return True, "Estoque editado com sucesso", estoque
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao editar estoque: {str(e)}")
            return False, f"Erro ao editar estoque: {str(e)}", None
    
    @staticmethod
    def excluir_estoque(estoque_id: int) -> Tuple[bool, str]:
        """
        Exclui um registro de estoque
        
        Args:
            estoque_id: ID do estoque
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            estoque = Estoque.query.get(estoque_id)
            if not estoque:
                return False, "Estoque não encontrado"
            
            produto_nome = estoque.produto.nome
            db.session.delete(estoque)
            db.session.commit()
            
            # Registrar atividade
            EstoqueService._registrar_atividade(
                tipo_atividade="Exclusão de Estoque",
                titulo="Estoque Excluído",
                descricao=f"Estoque excluído: {produto_nome}",
                modulo="Estoques",
                dados_extras={"estoque_id": estoque_id, "produto_nome": produto_nome}
            )
            
            current_app.logger.info(f"Estoque excluído: {produto_nome} (ID: {estoque_id})")
            
            return True, "Estoque excluído com sucesso"
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao excluir estoque: {str(e)}")
            return False, f"Erro ao excluir estoque: {str(e)}"
    
    @staticmethod
    def listar_estoques() -> List[Estoque]:
        """
        Lista todos os estoques
        
        Returns:
            List[Estoque]: Lista de estoques
        """
        try:
            return Estoque.query.all()
        except Exception as e:
            current_app.logger.error(f"Erro ao listar estoques: {str(e)}")
            return []
    
    @staticmethod
    def buscar_estoque(estoque_id: int) -> Optional[Estoque]:
        """
        Busca um estoque por ID
        
        Args:
            estoque_id: ID do estoque
            
        Returns:
            Optional[Estoque]: Estoque encontrado ou None
        """
        try:
            return Estoque.query.get(estoque_id)
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar estoque: {str(e)}")
            return None

    @staticmethod
    def atualizar_estoque(produto_id: int, quantidade: int, data_entrada: str, 
                         conferente: str = None, status: str = None, observacoes: str = '') -> Tuple[bool, str, Optional[Estoque]]:
        """
        Atualiza o estoque de um produto existente (soma à quantidade atual)
        
        Args:
            produto_id: ID do produto
            quantidade: Quantidade a ser adicionada
            data_entrada: Nova data de entrada
            conferente: Nome do conferente
            status: Novo status do estoque
            
        Returns:
            Tuple[bool, str, Optional[Estoque]]: (sucesso, mensagem, estoque)
        """
        try:
            # Buscar estoque existente
            estoque = Estoque.query.filter_by(produto_id=produto_id).first()
            if not estoque:
                return False, "Estoque não encontrado para este produto", None
            
            # Validações
            if quantidade < 0:
                return False, "Quantidade não pode ser negativa", None
            
            # Guardar quantidade anterior para movimentação
            quantidade_anterior = estoque.quantidade
            
            # Converter data_entrada de string para datetime
            try:
                if data_entrada:
                    data_entrada_dt = datetime.fromisoformat(
                        data_entrada.replace('Z', '+00:00')
                    )
                else:
                    data_entrada_dt = now_utc()
            except ValueError:
                data_entrada_dt = now_utc()
            
            # Usar nome do usuário logado como conferente se não fornecido
            if not conferente:
                conferente = session.get('usuario_nome', 'Sistema')
            
            # SOMAR à quantidade atual (não substituir)
            nova_quantidade = estoque.quantidade + quantidade
            
            # Atualizar dados
            estoque.quantidade = nova_quantidade
            estoque.data_entrada = data_entrada_dt
            estoque.conferente = conferente
            if status:
                estoque.status = status
            
            db.session.commit()
            
            # Registrar movimentação
            EstoqueService._registrar_movimentacao(
                produto_id=produto_id,
                tipo_movimentacao="Entrada",
                quantidade_anterior=quantidade_anterior,
                quantidade_movimentada=quantidade,
                quantidade_atual=nova_quantidade,
                motivo=f"Adição de estoque via formulário - Status: {status or estoque.status}",
                responsavel=conferente,
                observacoes=observacoes
            )
            
            # Registrar atividade
            EstoqueService._registrar_atividade(
                tipo_atividade="Atualização de Estoque",
                titulo="Estoque Atualizado",
                descricao=f"Estoque atualizado: {estoque.produto.nome} - Adicionado: {quantidade}, Total: {nova_quantidade}",
                modulo="Estoques",
                dados_extras={"estoque_id": estoque.id, "produto_id": produto_id, "quantidade_adicionada": quantidade, "quantidade_total": nova_quantidade}
            )
            
            current_app.logger.info(f"Estoque atualizado: {estoque.produto.nome} (ID: {estoque.id}) - Adicionado: {quantidade}, Total: {nova_quantidade}")
            
            return True, f"Estoque atualizado com sucesso! Adicionado: {quantidade}, Total: {nova_quantidade}", estoque
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao atualizar estoque: {str(e)}")
            return False, f"Erro ao atualizar estoque: {str(e)}", None

    @staticmethod
    def confirmar_inventario(usuario_nome: str) -> Tuple[bool, str, int]:
        """Confirma o inventário de todos os estoques registrando o responsável."""
        try:
            estoques = Estoque.query.all()
            if not estoques:
                return False, "Nenhum estoque disponível para confirmação.", 0

            responsavel = usuario_nome or session.get('usuario_nome', 'Sistema')
            agora = now_utc()

            for estoque in estoques:
                estoque.data_modificacao = agora
                estoque.data_conferencia = agora
                estoque.conferente = responsavel

            db.session.commit()

            EstoqueService._registrar_atividade(
                tipo_atividade="Inventário Confirmado",
                titulo="Inventário normalizado",
                descricao=f"Inventário confirmado por {responsavel} para {len(estoques)} itens",
                modulo="Estoques",
                dados_extras={"total_itens": len(estoques), "responsavel": responsavel}
            )

            current_app.logger.info(
                "Inventário confirmado por %s para %s itens",
                responsavel,
                len(estoques)
            )

            return True, "Inventário confirmado com sucesso.", len(estoques)
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao confirmar inventário: {str(e)}")
            return False, f"Erro ao confirmar inventário: {str(e)}", 0
    
    @staticmethod
    def _registrar_movimentacao(produto_id: int, tipo_movimentacao: str, quantidade_anterior: int, 
                               quantidade_movimentada: int, quantidade_atual: int, motivo: str, 
                               responsavel: str, observacoes: str = None) -> None:
        """
        Registra uma movimentação de estoque
        
        Args:
            produto_id: ID do produto
            tipo_movimentacao: Tipo da movimentação (Entrada, Saída, Ajuste)
            quantidade_anterior: Quantidade antes da movimentação
            quantidade_movimentada: Quantidade movimentada
            quantidade_atual: Quantidade após a movimentação
            motivo: Motivo da movimentação
            responsavel: Responsável pela movimentação
            observacoes: Observações adicionais
        """
        try:
            movimentacao = MovimentacaoEstoque(
                produto_id=produto_id,
                tipo_movimentacao=tipo_movimentacao,
                quantidade_anterior=quantidade_anterior,
                quantidade_movimentada=quantidade_movimentada,
                quantidade_atual=quantidade_atual,
                motivo=motivo,
                responsavel=responsavel,
                observacoes=observacoes
            )
            db.session.add(movimentacao)
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Erro ao registrar movimentação: {e}")
            # Não falhar se a movimentação não puder ser registrada
            pass

    @staticmethod
    def buscar_historico_movimentacao(produto_id: int) -> List[MovimentacaoEstoque]:
        """
        Busca o histórico de movimentação de um produto
        
        Args:
            produto_id: ID do produto
            
        Returns:
            List[MovimentacaoEstoque]: Lista de movimentações ordenadas por data (mais antigas primeiro)
        """
        try:
            return MovimentacaoEstoque.query.filter_by(produto_id=produto_id)\
                .order_by(MovimentacaoEstoque.data_movimentacao.asc()).all()
        except Exception as e:
            current_app.logger.error(f"Erro ao buscar histórico de movimentação: {str(e)}")
            return []

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
