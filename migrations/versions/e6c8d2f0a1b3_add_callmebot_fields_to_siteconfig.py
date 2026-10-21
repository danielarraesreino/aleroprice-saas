"""Adiciona campos de notificacao CallMeBot no SiteConfig

Revision ID: e6c8d2f0a1b3
Revises: d5b7c1e9f204
Create Date: 2026-08-21 17:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e6c8d2f0a1b3'
down_revision = 'd5b7c1e9f204'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotente: em produção essas colunas já foram criadas por
    # /bootstrap-demo?action=schema, e o Alembic ficou uma revisão atrás.
    existentes = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('site_config')}
    with op.batch_alter_table('site_config', schema=None) as batch_op:
        if 'callmebot_phone' not in existentes:
            batch_op.add_column(sa.Column('callmebot_phone', sa.String(length=20), nullable=True))
        if 'callmebot_apikey' not in existentes:
            batch_op.add_column(sa.Column('callmebot_apikey', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('site_config', schema=None) as batch_op:
        batch_op.drop_column('callmebot_apikey')
        batch_op.drop_column('callmebot_phone')
