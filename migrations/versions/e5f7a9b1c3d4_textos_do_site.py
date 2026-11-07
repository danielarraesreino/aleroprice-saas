"""Adiciona site_config.secao_titulo, secao_lead e pilares

Revision ID: e5f7a9b1c3d4
Revises: a1c3e5f7b9d2
Create Date: 2026-11-07 14:00:00.000000

Os textos fixos do site do expositor (título e frase da seção de produtos e os
destaques "Como trabalhamos") passam a ser editáveis no painel. Vazio = o site
usa o texto neutro da vibe. Idempotente: em produção o schema pode ter sido
alinhado antes por SQL.
"""
from alembic import op
import sqlalchemy as sa


revision = 'e5f7a9b1c3d4'
down_revision = 'a1c3e5f7b9d2'
branch_labels = None
depends_on = None

NOVAS = (('secao_titulo', sa.String(120)), ('secao_lead', sa.String(300)), ('pilares', sa.Text()))


def _colunas(tabela):
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def upgrade():
    cols = _colunas('site_config')
    with op.batch_alter_table('site_config', schema=None) as batch_op:
        for nome, tipo in NOVAS:
            if nome not in cols:
                batch_op.add_column(sa.Column(nome, tipo, nullable=True))


def downgrade():
    cols = _colunas('site_config')
    with op.batch_alter_table('site_config', schema=None) as batch_op:
        for nome, _ in reversed(NOVAS):
            if nome in cols:
                batch_op.drop_column(nome)
