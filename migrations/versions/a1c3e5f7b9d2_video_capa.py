"""Adiciona site_config.video_capa (capa viva em vídeo)

Revision ID: a1c3e5f7b9d2
Revises: c4e6a8b0d2f3
Create Date: 2026-11-06 22:00:00.000000

Idempotente: em produção o schema é alinhado por /bootstrap-demo?action=schema,
então a coluna pode já existir quando o Alembic chegar aqui.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1c3e5f7b9d2'
down_revision = 'c4e6a8b0d2f3'
branch_labels = None
depends_on = None


def _colunas(tabela):
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def upgrade():
    if 'video_capa' not in _colunas('site_config'):
        with op.batch_alter_table('site_config', schema=None) as batch_op:
            batch_op.add_column(sa.Column('video_capa', sa.String(length=300), nullable=True))


def downgrade():
    if 'video_capa' in _colunas('site_config'):
        with op.batch_alter_table('site_config', schema=None) as batch_op:
            batch_op.drop_column('video_capa')
