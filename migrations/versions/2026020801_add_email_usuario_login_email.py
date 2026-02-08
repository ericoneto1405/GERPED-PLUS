"""add email to usuario for login + reset password

Revision ID: 2026020801_add_email_usuario_login_email
Revises: 2026020601_fix_sequences_estoque_movimentacao
Create Date: 2026-02-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026020801_add_email_usuario_login_email"
down_revision = "2026020601_fix_sequences_estoque_movimentacao"
branch_labels = None
depends_on = None


def _dialect_name():
    bind = op.get_bind()
    return bind.dialect.name if bind is not None else ""


def upgrade():
    # Coluna nova (mantemos nullable para transicao; o app vai exigir para novos usuarios)
    op.add_column("usuario", sa.Column("email", sa.String(length=255), nullable=True))

    dialect = _dialect_name()
    if dialect in ("postgresql", "postgres"):
        # Unicidade case-insensitive para e-mail (ignora NULL).
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_usuario_email_lower "
            "ON usuario (lower(email)) WHERE email IS NOT NULL;"
        )
    else:
        # Fallback generico (pode ser case-sensitive em alguns bancos).
        op.create_index("ux_usuario_email", "usuario", ["email"], unique=True)


def downgrade():
    # Downgrade conservador: nao remove coluna/indice para evitar quebrar dados.
    return

