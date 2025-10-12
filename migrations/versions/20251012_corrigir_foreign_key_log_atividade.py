"""corrigir foreign key log_atividade ondelete set null

Revision ID: 20251012_001
Revises: 
Create Date: 2025-10-12 18:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251012_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Corrige a foreign key da tabela log_atividade para usar ondelete='SET NULL'
    quando um usuário for excluído.
    
    Para SQLite, precisamos recriar a tabela porque SQLite não suporta
    ALTER COLUMN ou modificação de constraints de foreign key.
    """
    # Para SQLite: precisamos recriar a tabela
    with op.batch_alter_table('log_atividade', schema=None) as batch_op:
        # Drop da foreign key antiga
        batch_op.drop_constraint('log_atividade_usuario_id_fkey', type_='foreignkey')
        
        # Recria a foreign key com ondelete='SET NULL'
        batch_op.create_foreign_key(
            'log_atividade_usuario_id_fkey',
            'usuario',
            ['usuario_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade():
    """Reverte a alteração"""
    with op.batch_alter_table('log_atividade', schema=None) as batch_op:
        # Drop da foreign key com SET NULL
        batch_op.drop_constraint('log_atividade_usuario_id_fkey', type_='foreignkey')
        
        # Recria a foreign key sem ondelete
        batch_op.create_foreign_key(
            'log_atividade_usuario_id_fkey',
            'usuario',
            ['usuario_id'],
            ['id']
        )

