"""fix sequences for estoque and movimentacao_estoque (postgres)

Revision ID: 2026020601_fix_sequences_estoque_movimentacao
Revises: 2025122302_adicionar_versao_pedido
Create Date: 2026-02-06 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "2026020601_fix_sequences_estoque_movimentacao"
down_revision = "2025122302_adicionar_versao_pedido"
branch_labels = None
depends_on = None


def _is_postgres():
    bind = op.get_bind()
    return bind and bind.dialect.name in ("postgresql", "postgres")


def upgrade():
    if not _is_postgres():
        return

    # Estoque
    op.execute("CREATE SEQUENCE IF NOT EXISTS estoque_id_seq;")
    op.execute(
        "SELECT setval('estoque_id_seq', COALESCE((SELECT max(id) FROM estoque), 0) + 1, false);"
    )
    op.execute("ALTER TABLE estoque ALTER COLUMN id SET DEFAULT nextval('estoque_id_seq');")

    # Movimentacao de estoque
    op.execute("CREATE SEQUENCE IF NOT EXISTS movimentacao_estoque_id_seq;")
    op.execute(
        "SELECT setval('movimentacao_estoque_id_seq', COALESCE((SELECT max(id) FROM movimentacao_estoque), 0) + 1, false);"
    )
    op.execute(
        "ALTER TABLE movimentacao_estoque ALTER COLUMN id SET DEFAULT nextval('movimentacao_estoque_id_seq');"
    )


def downgrade():
    # Não remove sequências/defaults para evitar quebrar instalações existentes.
    return
