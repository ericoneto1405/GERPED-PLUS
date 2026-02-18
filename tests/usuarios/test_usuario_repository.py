from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy.exc import SQLAlchemyError

from meu_app.usuarios.repositories import UsuarioRepository


def test_excluir_usuario_sucesso_via_orm():
    repo = UsuarioRepository()
    repo.db = SimpleNamespace(session=Mock())
    usuario = SimpleNamespace(id=2)

    resultado = repo.excluir(usuario)

    assert resultado is True
    repo.db.session.delete.assert_called_once_with(usuario)
    repo.db.session.commit.assert_called_once()
    repo.db.session.execute.assert_not_called()


def test_excluir_usuario_fallback_quando_tabela_token_nao_existe():
    repo = UsuarioRepository()
    session_mock = Mock()
    session_mock.delete.side_effect = SQLAlchemyError(
        '(psycopg.errors.UndefinedTable) relation "password_reset_token" does not exist'
    )
    repo.db = SimpleNamespace(session=session_mock)
    usuario = SimpleNamespace(id=2)

    resultado = repo.excluir(usuario)

    assert resultado is True
    assert session_mock.rollback.call_count == 1
    session_mock.execute.assert_called_once()
    session_mock.commit.assert_called_once()
