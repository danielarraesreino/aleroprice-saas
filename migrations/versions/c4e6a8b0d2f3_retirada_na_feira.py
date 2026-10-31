"""Adiciona site_config.retirada_na_feira e retirada_antecedencia

Revision ID: c4e6a8b0d2f3
Revises: b3d5f7a9c1e2
Create Date: 2026-10-31 15:00:00.000000

Idempotente: em produção o schema é alinhado por /bootstrap-demo?action=schema,
então as colunas podem já existir quando o Alembic chegar aqui.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c4e6a8b0d2f3'
down_revision = 'b3d5f7a9c1e2'
branch_labels = None
depends_on = None


def _colunas(tabela):
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def upgrade():
    cols = _colunas('site_config')
    with op.batch_alter_table('site_config', schema=None) as batch_op:
        if 'retirada_na_feira' not in cols:
            batch_op.add_column(sa.Column('retirada_na_feira', sa.Boolean(), nullable=True,
                                          server_default=sa.false()))
        if 'retirada_antecedencia' not in cols:
            batch_op.add_column(sa.Column('retirada_antecedencia', sa.Integer(), nullable=True,
                                          server_default='2'))


def downgrade():
    cols = _colunas('site_config')
    with op.batch_alter_table('site_config', schema=None) as batch_op:
        for nome in ('retirada_antecedencia', 'retirada_na_feira'):
            if nome in cols:
                batch_op.drop_column(nome)
