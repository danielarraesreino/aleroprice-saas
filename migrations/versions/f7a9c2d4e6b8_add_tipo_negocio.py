"""Adiciona restaurante.tipo_negocio ('bar' | 'artesao')

Revision ID: f7a9c2d4e6b8
Revises: e6c8d2f0a1b3
Create Date: 2026-10-20 12:00:00.000000

Idempotente: em produção o schema é alinhado por /bootstrap-demo?action=schema,
então a coluna pode já existir quando o Alembic chegar aqui.
"""
from alembic import op
import sqlalchemy as sa


revision = 'f7a9c2d4e6b8'
down_revision = 'e6c8d2f0a1b3'
branch_labels = None
depends_on = None


def _colunas(tabela):
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def upgrade():
    if 'tipo_negocio' not in _colunas('restaurante'):
        with op.batch_alter_table('restaurante', schema=None) as batch_op:
            batch_op.add_column(sa.Column('tipo_negocio', sa.String(length=20),
                                          nullable=True, server_default='bar'))
    op.execute("UPDATE restaurante SET tipo_negocio = 'bar' WHERE tipo_negocio IS NULL")


def downgrade():
    if 'tipo_negocio' in _colunas('restaurante'):
        with op.batch_alter_table('restaurante', schema=None) as batch_op:
            batch_op.drop_column('tipo_negocio')
