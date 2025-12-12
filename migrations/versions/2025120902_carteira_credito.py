"""cria carteira de creditos por cliente

Revision ID: 2025120902_carteira_credito
Revises: 2025120901_pagamento_anexos
Create Date: 2025-12-09 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = '2025120902_carteira_credito'
down_revision = '2025120901_pagamento_anexos'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'carteira_credito',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('cliente.id'), nullable=False),
        sa.Column('pedido_origem_id', sa.Integer(), sa.ForeignKey('pedido.id')),
        sa.Column('pagamento_origem_id', sa.Integer(), sa.ForeignKey('pagamento.id')),
        sa.Column('pagamento_anexo_id', sa.Integer(), sa.ForeignKey('pagamento_anexo.id')),
        sa.Column('caminho_anexo', sa.String(length=255), nullable=False),
        sa.Column('mime', sa.String(length=50)),
        sa.Column('tamanho', sa.Integer()),
        sa.Column('sha256', sa.String(length=64)),
        sa.Column('valor_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('saldo_disponivel', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='disponivel'),
        sa.Column('criado_por', sa.String(length=120)),
        sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('utilizado_em', sa.DateTime()),
        sa.Column('pedido_destino_id', sa.Integer(), sa.ForeignKey('pedido.id')),
        sa.Column('pagamento_destino_id', sa.Integer(), sa.ForeignKey('pagamento.id')),
    )
    op.create_index('ix_carteira_credito_cliente', 'carteira_credito', ['cliente_id'])


def downgrade():
    op.drop_index('ix_carteira_credito_cliente', table_name='carteira_credito')
    op.drop_table('carteira_credito')
