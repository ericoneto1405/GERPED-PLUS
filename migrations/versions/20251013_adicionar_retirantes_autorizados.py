"""Adicionar tabela de retirantes autorizados por cliente

Revision ID: 20251013_adicionar_retirantes
Revises: 20251012_corrigir_foreign_key_log_atividade
Create Date: 2025-10-13 16:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "20251013_adicionar_retirantes"
down_revision = "20251012_corrigir_foreign_key_log_atividade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cliente_retirante_autorizado",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False, index=True),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=False),
        sa.Column("observacoes", sa.String(length=255), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("cliente_id", "cpf", name="uq_cliente_retirante_cpf"),
    )


def downgrade() -> None:
    op.drop_table("cliente_retirante_autorizado")
