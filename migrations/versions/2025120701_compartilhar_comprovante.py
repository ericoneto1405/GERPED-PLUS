"""add shared receipt columns to pagamento

Revision ID: 2025120701_compartilhar_comprovante
Revises: 20251013_adicionar_retirantes_autorizados
Create Date: 2025-12-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025120701_compartilhar_comprovante'
down_revision = '20251013_adicionar_retirantes_autorizados'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    op.add_column('pagamento', sa.Column('compartilhado_disponivel', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('pagamento', sa.Column('compartilhado_por', sa.String(length=120), nullable=True))
    op.add_column('pagamento', sa.Column('compartilhado_em', sa.DateTime(), nullable=True))
    op.add_column('pagamento', sa.Column('compartilhado_usado_em', sa.DateTime(), nullable=True))
    op.add_column('pagamento', sa.Column('compartilhado_destino_pedido_id', sa.Integer(), nullable=True))
    op.add_column('pagamento', sa.Column('comprovante_compartilhado_origem_id', sa.Integer(), nullable=True))

    if not is_sqlite:
        op.create_foreign_key(
            'fk_pagamento_compartilhado_origem',
            'pagamento',
            'pagamento',
            ['comprovante_compartilhado_origem_id'],
            ['id']
        )

    op.alter_column('pagamento', 'compartilhado_disponivel', server_default=None)


def downgrade():
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if not is_sqlite:
        op.drop_constraint('fk_pagamento_compartilhado_origem', 'pagamento', type_='foreignkey')

    op.drop_column('pagamento', 'comprovante_compartilhado_origem_id')
    op.drop_column('pagamento', 'compartilhado_destino_pedido_id')
    op.drop_column('pagamento', 'compartilhado_usado_em')
    op.drop_column('pagamento', 'compartilhado_em')
    op.drop_column('pagamento', 'compartilhado_por')
    op.drop_column('pagamento', 'compartilhado_disponivel')
