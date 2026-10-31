"""Cria site_metrica (visitas e cliques por cliente e dia)

Revision ID: b3d5f7a9c1e2
Revises: d2e4a6c8b0f1
Create Date: 2026-10-31 12:00:00.000000

Idempotente: em produção a tabela pode nascer antes pelo create_all ou por
/bootstrap-demo?action=schema.
"""
from alembic import op
import sqlalchemy as sa


revision = 'b3d5f7a9c1e2'
down_revision = 'd2e4a6c8b0f1'
branch_labels = None
depends_on = None


def upgrade():
    if 'site_metrica' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'site_metrica',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('restaurant_id', sa.Integer(), sa.ForeignKey('restaurante.id'), nullable=False),
        sa.Column('dia', sa.Date(), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False, server_default='0'),
        sa.UniqueConstraint('restaurant_id', 'dia', 'tipo', name='uq_site_metrica'),
    )
    op.create_index('ix_site_metrica_restaurant_id', 'site_metrica', ['restaurant_id'])
    op.create_index('ix_site_metrica_dia', 'site_metrica', ['dia'])


def downgrade():
    if 'site_metrica' in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table('site_metrica')
