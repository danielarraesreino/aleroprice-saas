"""Ficha da loja do expositor: sobre, pagamento, políticas, atendimento, e-mail, Pix, TikTok,
selo de WhatsApp confirmado e prazo de produção por produto.

Revision ID: d2e4a6c8b0f1
Revises: c1d3f5a7b9e2
Create Date: 2026-10-24 23:00:00.000000

Idempotente: em produção o schema é alinhado por /bootstrap-demo?action=schema, então as colunas
podem já existir quando o Alembic chegar aqui.
"""
from alembic import op
import sqlalchemy as sa


revision = 'd2e4a6c8b0f1'
down_revision = 'c1d3f5a7b9e2'
branch_labels = None
depends_on = None

SITE_CONFIG = (
    ('tiktok_url', sa.String(length=200)),
    ('sobre', sa.Text()),
    ('pagamento', sa.String(length=200)),
    ('politicas', sa.Text()),
    ('atendimento', sa.String(length=120)),
    ('email', sa.String(length=120)),
    ('desconto_pix_pct', sa.Integer()),
    ('whatsapp_confirmado', sa.Boolean()),
)


def _colunas(tabela):
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def upgrade():
    existentes = _colunas('site_config')
    with op.batch_alter_table('site_config', schema=None) as batch_op:
        for nome, tipo in SITE_CONFIG:
            if nome not in existentes:
                batch_op.add_column(sa.Column(nome, tipo, nullable=True))
    if 'prazo_dias' not in _colunas('site_produto'):
        with op.batch_alter_table('site_produto', schema=None) as batch_op:
            batch_op.add_column(sa.Column('prazo_dias', sa.Integer(), nullable=True))


def downgrade():
    existentes = _colunas('site_config')
    with op.batch_alter_table('site_config', schema=None) as batch_op:
        for nome, _ in SITE_CONFIG:
            if nome in existentes:
                batch_op.drop_column(nome)
    if 'prazo_dias' in _colunas('site_produto'):
        with op.batch_alter_table('site_produto', schema=None) as batch_op:
            batch_op.drop_column('prazo_dias')
