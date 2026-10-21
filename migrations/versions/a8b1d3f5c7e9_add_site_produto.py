"""Cria site_produto (produtos do hotsite de artesão)

Revision ID: a8b1d3f5c7e9
Revises: f7a9c2d4e6b8
Create Date: 2026-10-20 22:00:00.000000

Idempotente: em produção `/bootstrap-demo?action=schema` (create_all) pode já
ter criado a tabela.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a8b1d3f5c7e9'
down_revision = 'f7a9c2d4e6b8'
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table('site_produto'):
        return
    op.create_table(
        'site_produto',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('restaurant_id', sa.Integer(), sa.ForeignKey('restaurante.id'), nullable=False),
        sa.Column('nome', sa.String(length=120), nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('categoria', sa.String(length=60)),
        sa.Column('preco', sa.Numeric(8, 2)),
        sa.Column('sob_encomenda', sa.Boolean(), server_default=sa.false()),
        sa.Column('imagem', sa.String(length=300)),
        sa.Column('destaque', sa.Boolean(), server_default=sa.false()),
        sa.Column('ordem', sa.Integer(), server_default='0'),
        sa.Column('ativo', sa.Boolean(), server_default=sa.true()),
    )
    op.create_index('ix_site_produto_restaurant_id', 'site_produto', ['restaurant_id'])
    op.create_index('ix_site_produto_categoria', 'site_produto', ['categoria'])
    op.create_index('ix_site_produto_ordem', 'site_produto', ['ordem'])
    op.create_index('ix_site_produto_ativo', 'site_produto', ['ativo'])


def downgrade():
    if sa.inspect(op.get_bind()).has_table('site_produto'):
        op.drop_table('site_produto')
