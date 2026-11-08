"""Adiciona promocao.codigo (cupom que o cliente diz no balcão)

Revision ID: f1a3c5e7b9d2
Revises: e5f7a9b1c3d4
Create Date: 2026-11-07 12:00:00.000000

Idempotente: em produção o schema é alinhado por /bootstrap-demo?action=schema,
então a coluna pode já existir quando o Alembic chegar aqui.
"""
from alembic import op
import sqlalchemy as sa


revision = 'f1a3c5e7b9d2'
down_revision = 'e5f7a9b1c3d4'
branch_labels = None
depends_on = None


def _colunas(tabela):
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def upgrade():
    if 'codigo' not in _colunas('promocao'):
        with op.batch_alter_table('promocao', schema=None) as batch_op:
            batch_op.add_column(sa.Column('codigo', sa.String(length=20), nullable=True))


def downgrade():
    if 'codigo' in _colunas('promocao'):
        with op.batch_alter_table('promocao', schema=None) as batch_op:
            batch_op.drop_column('codigo')
