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
        self._session = session
        self._model = model or Cliente

    @property
    def session(self):
        return self._session or db.session

    @property
    def model(self):
        return self._model

    def buscar_por_id(self, cliente_id: int) -> Optional[Cliente]:
        try:
            return self.model.query.get(cliente_id)
        except SQLAlchemyError as e:
            print(f"Erro ao buscar cliente por ID {cliente_id}: {str(e)}")
            return None

    def buscar_por_nome(self, nome: str) -> Optional[Cliente]:
        try:
            return self.model.query.filter_by(nome=nome).first()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar cliente por nome '{nome}': {str(e)}")
            return None

    def buscar_por_cpf_cnpj(self, cpf_cnpj: str) -> Optional[Cliente]:
        try:
            return self.model.query.filter_by(cpf_cnpj=cpf_cnpj).first()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar cliente por CPF/CNPJ: {str(e)}")
            return None

    def buscar_por_nome_parcial(self, nome: str) -> List[Cliente]:
        try:
            return self.model.query.filter(self.model.nome.ilike(f"%{nome}%")).all()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar clientes por nome parcial '{nome}': {str(e)}")
            return []

    def listar_todos(self) -> List[Cliente]:
        try:
            return self.model.query.order_by(self.model.nome).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar clientes: {str(e)}")
            return []

    def listar_por_cidade(self, cidade: str) -> List[Cliente]:
        try:
            return self.model.query.filter_by(cidade=cidade).order_by(self.model.nome).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar clientes por cidade '{cidade}': {str(e)}")
            return []

    def criar(self, cliente: Cliente) -> Cliente:
        try:
            self.session.add(cliente)
            self.session.commit()
            return cliente
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Erro ao criar cliente: {str(e)}")
            raise

    def atualizar(self, cliente: Cliente) -> Cliente:
        try:
            self.session.commit()
            return cliente
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Erro ao atualizar cliente: {str(e)}")
            raise

    def excluir(self, cliente: Cliente) -> None:
        try:
            self.session.delete(cliente)
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Erro ao excluir cliente: {str(e)}")
            raise

    def contar_total(self) -> int:
        try:
            return self.model.query.count()
        except SQLAlchemyError as e:
            print(f"Erro ao contar clientes: {str(e)}")
            return 0

    def verificar_nome_existe(self, nome: str, excluir_id: Optional[int] = None) -> bool:
        try:
            query = self.model.query.filter_by(nome=nome)
            if excluir_id is not None:
                query = query.filter(self.model.id != excluir_id)
            return query.first() is not None
        except SQLAlchemyError as e:
            print(f"Erro ao verificar nome do cliente: {str(e)}")
            return False


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

    def buscar_por_cliente_e_cpf(self, cliente_id: int, cpf: str) -> Optional[ClienteRetiranteAutorizado]:
        try:
            return (
                self.model.query.filter_by(cliente_id=cliente_id, cpf=cpf)
                .one_or_none()
            )
        except SQLAlchemyError as e:
            print(f"Erro ao buscar retirante autorizado por CPF: {e}")
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
