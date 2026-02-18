"""
Repository para o módulo de usuários.

Implementa o padrão Repository para acesso a dados de usuários.
"""

from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from ..models import db, Usuario


class UsuarioRepository:
    """Repository para operações de banco de dados de usuários."""
    
    def __init__(self):
        """Inicializa o repositório"""
        self.db = db
    
    def buscar_por_id(self, usuario_id: int) -> Optional[Usuario]:
        """Busca usuário por ID."""
        try:
            return Usuario.query.get(usuario_id)
        except SQLAlchemyError as e:
            print(f"Erro ao buscar usuário por ID {usuario_id}: {str(e)}")
            return None
    
    def buscar_por_nome(self, nome: str) -> Optional[Usuario]:
        """Busca usuário por nome (único)."""
        try:
            return Usuario.query.filter_by(nome=nome).first()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar usuário por nome '{nome}': {str(e)}")
            return None

    def buscar_por_email(self, email: str) -> Optional[Usuario]:
        """Busca usuário por email (único)."""
        try:
            return Usuario.query.filter_by(email=email).first()
        except SQLAlchemyError as e:
            print(f"Erro ao buscar usuário por email '{email}': {str(e)}")
            return None
    
    def listar_todos(self) -> List[Usuario]:
        """Lista todos os usuários."""
        try:
            return Usuario.query.order_by(Usuario.nome).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar usuários: {str(e)}")
            return []
    
    def listar_por_tipo(self, tipo: str) -> List[Usuario]:
        """Lista usuários por tipo (admin ou comum)."""
        try:
            return Usuario.query.filter_by(tipo=tipo).order_by(Usuario.nome).all()
        except SQLAlchemyError as e:
            print(f"Erro ao listar usuários por tipo '{tipo}': {str(e)}")
            return []
    
    def criar(self, usuario: Usuario) -> Usuario:
        """Cria novo usuário."""
        try:
            self.db.session.add(usuario)
            self.db.session.commit()
            return usuario
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao criar usuário: {str(e)}")
            raise
    
    def atualizar(self, usuario: Usuario) -> Usuario:
        """Atualiza usuário existente."""
        try:
            self.db.session.commit()
            return usuario
        except SQLAlchemyError as e:
            self.db.session.rollback()
            print(f"Erro ao atualizar usuário: {str(e)}")
            raise
    
    def excluir(self, usuario: Usuario) -> bool:
        """Exclui usuário do banco de dados."""
        try:
            self.db.session.delete(usuario)
            self.db.session.commit()
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            erro_msg = str(e).lower()
            # Compatibilidade com bases antigas que ainda não possuem a tabela
            # password_reset_token.
            if "password_reset_token" in erro_msg and "does not exist" in erro_msg:
                try:
                    self.db.session.execute(
                        text("DELETE FROM usuario WHERE id = :usuario_id"),
                        {"usuario_id": usuario.id},
                    )
                    self.db.session.commit()
                    return True
                except SQLAlchemyError:
                    self.db.session.rollback()
                    raise
            print(f"Erro ao excluir usuário: {str(e)}")
            raise
    
    def verificar_nome_existe(self, nome: str, excluir_id: Optional[int] = None) -> bool:
        """
        Verifica se já existe usuário com o nome.
        
        Args:
            nome: Nome a verificar
            excluir_id: ID do usuário a excluir da verificação (para edição)
            
        Returns:
            True se nome já existe
        """
        try:
            query = Usuario.query.filter_by(nome=nome)
            if excluir_id:
                query = query.filter(Usuario.id != excluir_id)
            return query.first() is not None
        except SQLAlchemyError as e:
            print(f"Erro ao verificar nome '{nome}': {str(e)}")
            return False

    def verificar_email_existe(self, email: str, excluir_id: Optional[int] = None) -> bool:
        """Verifica se já existe usuário com o email."""
        try:
            query = Usuario.query.filter_by(email=email)
            if excluir_id:
                query = query.filter(Usuario.id != excluir_id)
            return query.first() is not None
        except SQLAlchemyError as e:
            print(f"Erro ao verificar email '{email}': {str(e)}")
            return False
    
    def contar_total(self) -> int:
        """Conta total de usuários."""
        try:
            return Usuario.query.count()
        except SQLAlchemyError as e:
            print(f"Erro ao contar usuários: {str(e)}")
            return 0
