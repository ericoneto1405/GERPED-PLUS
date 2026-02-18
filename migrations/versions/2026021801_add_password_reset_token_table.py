"""add password_reset_token table

Revision ID: 2026021801_add_password_reset_token_table
Revises: 2026020801_add_email_usuario_login_email
Create Date: 2026-02-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026021801_add_password_reset_token_table"
down_revision = "2026020801_add_email_usuario_login_email"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("password_reset_token"):
        return

    op.create_table(
        "password_reset_token",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuario.id"), nullable=False),
        sa.Column("token", sa.String(length=128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("usado", sa.Boolean(), nullable=True, server_default=sa.false()),
    )
    op.create_index(
        "ix_password_reset_token_usuario_id",
        "password_reset_token",
        ["usuario_id"],
        unique=False,
    )


def downgrade():
    # Downgrade conservador: nao remove tabela para evitar perda de historico.
    return
