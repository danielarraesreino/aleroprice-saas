"""Nome do tenant do Bar da Vila + remoção dos pratos legados de teste.

Migration só de dados, para acertar duas heranças do banco de demo:

1. A migration `a1c4f7e9d2b0` adotou o tenant que era "Restaurante Teste" como o
   Bar da Vila (gravou slug, domínio e todo o conteúdo do site nele), mas não
   mexeu no `restaurante.nome`. O site público lê o nome de `site_config`, então
   ele já aparecia certo — mas o sistema interno lê `restaurante.nome`, e o dono
   do bar continuava vendo "Restaurante Teste" no topo do próprio dashboard.

2. Sobraram no tenant 4 pratos de um seed antigo, anteriores ao bar (Hamburguer
   sem preço, Pastel de Carne, Pastel de Queijo, Coxinha). Não são do cardápio da
   casa e sujam ficha técnica, cardápio e relatórios.

A remoção é DEFENSIVA: cada prato só é apagado se nenhuma outra tabela apontar
para ele (ficha técnica, item de cardápio, venda, previsão, sazonalidade,
desperdício, meta). Se um deles tiver ganhado histórico em algum ambiente, ele
fica onde está e a migration segue — é preferível um prato a mais no cardápio do
que um relatório com venda órfã.

Revision ID: c3e6b9a41d52
Revises: b2d5a8c3f1e7
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3e6b9a41d52'
down_revision = 'b2d5a8c3f1e7'
branch_labels = None
depends_on = None


BARDAVILA_SLUG = 'bar-da-vila'
NOME_ANTIGO = 'Restaurante Teste'
NOME_NOVO = 'Bar da Vila'

PRATOS_LEGADOS = ['Hamburguer', 'Pastel de Carne', 'Pastel de Queijo', 'Coxinha']

# Toda tabela com FK para pratos.id. Se alguma delas referencia o prato, ele fica.
REFERENCIAS = [
    ('prato_insumo', 'prato_id'),
    ('cardapio_item', 'prato_id'),
    ('historico_vendas', 'prato_id'),
    ('previsao_demanda', 'prato_id'),
    ('fator_sazonalidade', 'prato_id'),
    ('registro_desperdicio', 'prato_id'),
    ('meta_desperdicio', 'prato_id'),
]


def upgrade():
    conn = op.get_bind()

    rid = conn.execute(
        sa.text('SELECT id FROM restaurante WHERE slug = :slug'),
        {'slug': BARDAVILA_SLUG},
    ).scalar()

    if rid is None:
        # Banco sem o tenant do bar (instalação limpa): nada a corrigir.
        return

    conn.execute(
        sa.text('UPDATE restaurante SET nome = :novo '
                'WHERE id = :rid AND nome = :antigo'),
        {'novo': NOME_NOVO, 'antigo': NOME_ANTIGO, 'rid': rid},
    )

    for nome in PRATOS_LEGADOS:
        prato_id = conn.execute(
            sa.text('SELECT id FROM pratos WHERE nome = :nome AND restaurant_id = :rid'),
            {'nome': nome, 'rid': rid},
        ).scalar()
        if prato_id is None:
            continue

        referenciado = any(
            conn.execute(
                sa.text(f'SELECT 1 FROM {tabela} WHERE {coluna} = :pid LIMIT 1'),
                {'pid': prato_id},
            ).scalar()
            for tabela, coluna in REFERENCIAS
        )
        if referenciado:
            continue

        conn.execute(sa.text('DELETE FROM pratos WHERE id = :pid'), {'pid': prato_id})


def downgrade():
    # Só o nome volta. Os pratos legados eram lixo de seed, sem conteúdo próprio
    # para restaurar — recriá-los aqui inventaria dados que nunca existiram.
    conn = op.get_bind()
    conn.execute(
        sa.text('UPDATE restaurante SET nome = :antigo '
                'WHERE slug = :slug AND nome = :novo'),
        {'antigo': NOME_ANTIGO, 'novo': NOME_NOVO, 'slug': BARDAVILA_SLUG},
    )
