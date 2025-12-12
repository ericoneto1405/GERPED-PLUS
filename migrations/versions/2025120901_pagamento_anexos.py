"""cria tabela pagamento_anexo e migra comprovantes principais

Revision ID: 2025120901_pagamento_anexos
Revises: 2025120701_compartilhar_comprovante
Create Date: 2025-12-09 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '2025120901_pagamento_anexos'
down_revision = '2025120701_compartilhar_comprovante'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'pagamento_anexo',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('pagamento_id', sa.Integer(), sa.ForeignKey('pagamento.id', ondelete='CASCADE'), nullable=False),
        sa.Column('caminho', sa.String(length=255), nullable=False),
        sa.Column('mime', sa.String(length=50), nullable=True),
        sa.Column('tamanho', sa.Integer(), nullable=True),
        sa.Column('sha256', sa.String(length=64), nullable=True),
        sa.Column('principal', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('criado_em', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_pagamento_anexo_pagamento_id', 'pagamento_anexo', ['pagamento_id'])
    op.create_unique_constraint('uq_pagamento_anexo_sha256', 'pagamento_anexo', ['sha256'])

    conn = op.get_bind()
    rows = conn.execute(sa.text("""
        SELECT id, caminho_recibo, recibo_mime, recibo_tamanho, recibo_sha256
        FROM pagamento
        WHERE caminho_recibo IS NOT NULL
    """)).fetchall()

    if rows:
        now = datetime.utcnow()
        insert_stmt = sa.text("""
            INSERT INTO pagamento_anexo
                (pagamento_id, caminho, mime, tamanho, sha256, principal, criado_em, atualizado_em)
            VALUES
                (:pagamento_id, :caminho, :mime, :tamanho, :sha256, :principal, :criado_em, :atualizado_em)
        """)
        for row in rows:
            conn.execute(
                insert_stmt,
                pagamento_id=row.id,
                caminho=row.caminho_recibo,
                mime=row.recibo_mime,
                tamanho=row.recibo_tamanho,
                sha256=row.recibo_sha256,
                principal=True,
                criado_em=now,
                atualizado_em=now
            )


def downgrade():
    op.drop_constraint('uq_pagamento_anexo_sha256', 'pagamento_anexo', type_='unique')
    op.drop_index('ix_pagamento_anexo_pagamento_id', table_name='pagamento_anexo')
    op.drop_table('pagamento_anexo')
