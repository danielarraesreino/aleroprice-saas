"""Promoção com data de início e recorrência semanal.

Antes só existia `validade` (fim). Não dava pra agendar uma promoção pra
começar depois, nem cadastrar o "Lanche de Quarta" — que se repete toda semana.

Revision ID: b2d5a8c3f1e7
Revises: a1c4f7e9d2b0
"""
from alembic import op
import sqlalchemy as sa


revision = 'b2d5a8c3f1e7'
down_revision = 'a1c4f7e9d2b0'
branch_labels = None
depends_on = None


def upgrade():
    # `promocao` nasceu do db.create_all() e pode não existir num banco novo.
    if 'promocao' not in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    with op.batch_alter_table('promocao') as batch:
        batch.add_column(sa.Column('data_inicio', sa.Date(), nullable=True))
        batch.add_column(sa.Column('dia_semana', sa.Integer(), nullable=True))


def downgrade():
    if 'promocao' not in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    with op.batch_alter_table('promocao') as batch:
        batch.drop_column('dia_semana')
        batch.drop_column('data_inicio')
