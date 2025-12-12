"""corrigir foreign key log_atividade ondelete set null

Revision ID: 20251012_corrigir_foreign_key_log_atividade
Revises: 
Create Date: 2025-10-12 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251012_corrigir_foreign_key_log_atividade'
down_revision = None
branch_labels = None
depends_on = None

FK_NAME = 'log_atividade_usuario_id_fkey'


def _fk_exists():
    """Verifica se a FK já está registrada na base."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(fk.get('name') == FK_NAME for fk in inspector.get_foreign_keys('log_atividade'))


def upgrade():
    """
    Corrige a foreign key da tabela log_atividade para usar ondelete='SET NULL'
    quando um usuário for excluído.
    
    Para SQLite, precisamos recriar a tabela porque SQLite não suporta
    ALTER COLUMN ou modificação de constraints de foreign key.
    """
    # Para SQLite: precisamos recriar a tabela
    fk_existe = _fk_exists()
    with op.batch_alter_table('log_atividade', schema=None) as batch_op:
        if fk_existe:
            batch_op.drop_constraint(FK_NAME, type_='foreignkey')

        # Recria a foreign key com ondelete='SET NULL'
        batch_op.create_foreign_key(
            FK_NAME,
            'usuario',
            ['usuario_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade():
    """Reverte a alteração"""
    fk_existe = _fk_exists()
    with op.batch_alter_table('log_atividade', schema=None) as batch_op:
        if fk_existe:
            batch_op.drop_constraint(FK_NAME, type_='foreignkey')

        # Recria a foreign key sem ondelete
        batch_op.create_foreign_key(
            FK_NAME,
            'usuario',
            ['usuario_id'],
            ['id']
        )

