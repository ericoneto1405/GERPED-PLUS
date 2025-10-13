"""
Repository para o módulo de clientes.

Implementa o padrão Repository para acesso a dados de clientes,
separando a lógica de acesso ao banco de dados da lógica de negócio.
"""

from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError
from ..models import db, Cliente, ClienteRetiranteAutorizado


class ClienteRepository:
    """
    Repository para operações de banco de dados de clientes.
    
    Esta classe encapsula todas as operações de acesso a dados,
    permitindo testes independentes e facilitando manutenção.
    """
    
    def __init__(self, session=None, model=None):
        """Inicializa o repositório"""
        self._session = session
        self._model = model

    @property
    def session(self):
        """Retorna a sessão ativa"""
        return self._session or db.session

    @property
    def model(self):
        """Retorna o modelo associado"""
        return self._model or Cliente


class RetiranteAutorizadoRepository:
    """Repository para retirantes autorizados de um cliente."""

    def __init__(self, session=None, model=None):
        self._session = session
        self._model = model or ClienteRetiranteAutorizado

    @property
    def session(self):
        return self._session or db.session

    @property
    def model(self):
        return self._model

    def listar_por_cliente(self, cliente_id: int) -> List[ClienteRetiranteAutorizado]:
        try:
            return (
                self.model.query.filter_by(cliente_id=cliente_id)
                .order_by(self.model.nome)
                .all()
            )
        except SQLAlchemyError as e:
            print(f"Erro ao listar retirantes autorizados: {e}")
            return []

    def buscar_por_id(self, retirante_id: int) -> Optional[ClienteRetiranteAutorizado]:
        try:
            return self.model.query.get(retirante_id)
        except SQLAlchemyError as e:
            print(f"Erro ao buscar retirante autorizado: {e}")
            return None

    def criar(self, retirante: ClienteRetiranteAutorizado) -> ClienteRetiranteAutorizado:
        try:
            self.session.add(retirante)
            self.session.commit()
            return retirante
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Erro ao criar retirante autorizado: {e}")
            raise

    def atualizar(self, retirante: ClienteRetiranteAutorizado) -> ClienteRetiranteAutorizado:
        try:
            self.session.commit()
            return retirante
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Erro ao atualizar retirante autorizado: {e}")
            raise

    def excluir(self, retirante: ClienteRetiranteAutorizado) -> None:
        try:
            self.session.delete(retirante)
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Erro ao excluir retirante autorizado: {e}")
            raise
    
    def buscar_por_id(self, cliente_id: int) -> Optional[Cliente]:
        """
        Busca cliente por ID.
        
        Args:
            cliente_id: ID do cliente
            
        Returns:
            Cliente encontrado ou None
        """
        try:
            return self.model.query.get(cliente_id)
        except SQLAlchemyError as e:
            print(f"Erro ao buscar cliente por ID {cliente_id}: {str(e)}")
            return None
    
    def buscar_por_nome(self, nome: str) -> Optional[Cliente]:
        """
        Busca cliente por nome exato.
        
        Args:
            nome: Nome do cliente
            
        Returns:
            Cliente encontrado ou None
        """
        try:
            return self.model.query.filter_by(nome=nome).first()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar cliente por nome '{nome}': {str(e)}")
            return None
    
    def buscar_por_cpf_cnpj(self, cpf_cnpj: str) -> Optional[Cliente]:
        """
        Busca cliente por CPF/CNPJ.
        
        Args:
            cpf_cnpj: CPF ou CNPJ do cliente
            
        Returns:
            Cliente encontrado ou None
        """
        try:
            return self.model.query.filter_by(cpf_cnpj=cpf_cnpj).first()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar cliente por CPF/CNPJ: {str(e)}")
            return None
    
    def buscar_por_nome_parcial(self, nome: str) -> List[Cliente]:
        """
        Busca clientes por nome parcial (LIKE).
        
        Args:
            nome: Parte do nome do cliente
            
        Returns:
            Lista de clientes encontrados
        """
        try:
            return self.model.query.filter(self.model.nome.ilike(f'%{nome}%')).all()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar clientes por nome parcial '{nome}': {str(e)}")
            return []
    
    def listar_todos(self) -> List[Cliente]:
        """
        Lista todos os clientes.
        
        Returns:
            Lista de todos os clientes
        """
        try:
            return self.model.query.order_by(self.model.nome).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar clientes: {str(e)}")
            return []
    
    def listar_por_cidade(self, cidade: str) -> List[Cliente]:
        """
        Lista clientes por cidade.
        
        Args:
            cidade: Nome da cidade
            
        Returns:
            Lista de clientes da cidade
        """
        try:
            return self.model.query.filter_by(cidade=cidade).order_by(self.model.nome).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar clientes por cidade '{cidade}': {str(e)}")
            return []
    
    def criar(self, cliente: Cliente) -> Cliente:
        """
        Cria novo cliente no banco de dados.
        
        Args:
            cliente: Objeto Cliente a ser criado
            
        Returns:
            Cliente criado com ID
            
        Raises:
            SQLAlchemyError: Em caso de erro no banco
        """
        try:
            self.session.add(cliente)
            self.session.commit()
            return cliente
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Erro ao criar cliente: {str(e)}")
            raise
    
    def atualizar(self, cliente: Cliente) -> Cliente:
        """
        Atualiza cliente existente.
        
        Args:
            cliente: Cliente com dados atualizados
            
        Returns:
            Cliente atualizado
            
        Raises:
            SQLAlchemyError: Em caso de erro no banco
        """
        try:
            self.session.commit()
            return cliente
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Erro ao atualizar cliente: {str(e)}")
            raise
    
    def excluir(self, cliente: Cliente) -> bool:
        """
        Exclui cliente do banco de dados.
        
        Args:
            cliente: Cliente a ser excluído
            
        Returns:
            True se excluído com sucesso
            
        Raises:
            SQLAlchemyError: Em caso de erro no banco
        """
        try:
            self.session.delete(cliente)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Erro ao excluir cliente: {str(e)}")
            raise
    
    def contar_total(self) -> int:
        """
        Conta total de clientes cadastrados.
        
        Returns:
            Número total de clientes
        """
        try:
            return self.model.query.count()
        except SQLAlchemyError as e:
            print(f"Erro ao contar clientes: {str(e)}")
            return 0
    
    def verificar_nome_existe(self, nome: str, excluir_id: Optional[int] = None) -> bool:
        """
        Verifica se já existe cliente com o nome.
        
        Args:
            nome: Nome a verificar
            excluir_id: ID do cliente a excluir da verificação (para edição)
            
        Returns:
            True se nome já existe
        """
        try:
            query = self.model.query.filter_by(nome=nome)
            if excluir_id:
                query = query.filter(self.model.id != excluir_id)
            return query.first() is not None
        except SQLAlchemyError as e:
            print(f"Erro ao verificar nome '{nome}': {str(e)}")
            return False
