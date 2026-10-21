"""Adiciona site_config.logo (marca do negocio)

Revision ID: b9c2e4a6d8f0
Revises: a8b1d3f5c7e9
Create Date: 2026-10-20 23:00:00.000000

Idempotente (em producao o schema pode ter sido alinhado por action=schema).
"""
from alembic import op
import sqlalchemy as sa


revision = 'b9c2e4a6d8f0'
down_revision = 'a8b1d3f5c7e9'
branch_labels = None
depends_on = None


def _colunas():
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns('site_config')}


def upgrade():
    if 'logo' not in _colunas():
        with op.batch_alter_table('site_config', schema=None) as batch_op:
            batch_op.add_column(sa.Column('logo', sa.String(length=300), nullable=True))


def downgrade():
    if 'logo' in _colunas():
        with op.batch_alter_table('site_config', schema=None) as batch_op:
            batch_op.drop_column('logo')
