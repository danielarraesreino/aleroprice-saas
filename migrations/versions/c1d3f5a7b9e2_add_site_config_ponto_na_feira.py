"""Adiciona site_config.lat/lng/ponto_na_feira/na_feira_em (mapa da Feira)

Revision ID: c1d3f5a7b9e2
Revises: b9c2e4a6d8f0
Create Date: 2026-10-21 10:00:00.000000

Idempotente (em producao o schema pode ter sido alinhado por action=schema).
"""
from alembic import op
import sqlalchemy as sa


revision = 'c1d3f5a7b9e2'
down_revision = 'b9c2e4a6d8f0'
branch_labels = None
depends_on = None

COLUNAS = (
    ('lat', sa.Float()),
    ('lng', sa.Float()),
    ('ponto_na_feira', sa.String(length=120)),
    ('na_feira_em', sa.Date()),
)


def _existentes():
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns('site_config')}


def upgrade():
    ja = _existentes()
    with op.batch_alter_table('site_config', schema=None) as batch_op:
        for nome, tipo in COLUNAS:
            if nome not in ja:
                batch_op.add_column(sa.Column(nome, tipo, nullable=True))


def downgrade():
    ja = _existentes()
    with op.batch_alter_table('site_config', schema=None) as batch_op:
        for nome, _ in reversed(COLUNAS):
            if nome in ja:
                batch_op.drop_column(nome)
