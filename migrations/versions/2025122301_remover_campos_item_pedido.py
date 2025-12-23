"""remover campos de custo do item_pedido

Revision ID: 2025122301_remover_campos_item_pedido
Revises: 2025121501_pagamento_anexo_valor
Create Date: 2025-12-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025122301_remover_campos_item_pedido'
down_revision = '2025121501_pagamento_anexo_valor'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('item_pedido') as batch_op:
        batch_op.drop_column('preco_compra')
        batch_op.drop_column('valor_total_compra')
        batch_op.drop_column('lucro_bruto')


def downgrade():
    with op.batch_alter_table('item_pedido') as batch_op:
        batch_op.add_column(sa.Column('preco_compra', sa.Numeric(10, 2), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('valor_total_compra', sa.Numeric(10, 2), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('lucro_bruto', sa.Numeric(10, 2), nullable=False, server_default=sa.text('0')))
