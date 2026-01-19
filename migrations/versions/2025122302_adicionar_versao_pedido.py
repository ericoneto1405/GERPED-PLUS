"""adicionar versao ao pedido

Revision ID: 2025122302_adicionar_versao_pedido
Revises: 2025122301_remover_campos_item_pedido
Create Date: 2025-12-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025122302_adicionar_versao_pedido'
down_revision = '2025122301_remover_campos_item_pedido'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('pedido') as batch_op:
        batch_op.add_column(
            sa.Column('versao', sa.Integer(), nullable=False, server_default=sa.text('1'))
        )


def downgrade():
    with op.batch_alter_table('pedido') as batch_op:
        batch_op.drop_column('versao')
