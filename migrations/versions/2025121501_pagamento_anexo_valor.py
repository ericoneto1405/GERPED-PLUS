"""add valor column to pagamento_anexo

Revision ID: 2025121501_pagamento_anexo_valor
Revises: 2025120902_carteira_credito
Create Date: 2025-12-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2025121501_pagamento_anexo_valor'
down_revision = '2025120902_carteira_credito'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('pagamento_anexo', sa.Column('valor', sa.Numeric(10, 2), nullable=True))


def downgrade():
    op.drop_column('pagamento_anexo', 'valor')
