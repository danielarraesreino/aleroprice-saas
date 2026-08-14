"""Uniques globais viram por-tenant (prato.nome, produto.codigo, categoria_desperdicio.nome)

Com um cliente só, `nome UNIQUE` nunca doeu. Com dois bares, dói no primeiro
dia: "Caipirinha" e "Porção de calabresa" existem em toda casa, e `produto.codigo`
é EAN — o segundo bar que importar uma NF-e com o mesmo produto quebra.

Segue o precedente de `b17a080954d4` (fornecedor.cnpj), com dois cuidados que
aquela não precisou ter:

1. O nome da constraint **varia** e é descoberto em runtime. `Prato.nome` era
   `unique=True` sem `index=True`, então o Postgres gerou uma CONSTRAINT
   (`pratos_nome_key`), não um índice — dropar pelo nome errado falha.
2. SQLite não dropa constraint sem `batch_alter_table` (recria a tabela).

Tolerante de propósito: se o unique antigo não existir (banco criado por
`create_all()` de uma versão mais nova), segue em frente.

Revision ID: d5b7c1e9f204
Revises: c3e6b9a41d52
"""
from alembic import op
import sqlalchemy as sa

revision = 'd5b7c1e9f204'
down_revision = 'c3e6b9a41d52'
branch_labels = None
depends_on = None


# (tabela, coluna, nome do unique novo)
ALVOS = [
    ('produto', 'codigo', 'uq_produto_codigo_restaurant'),
    ('pratos', 'nome', 'uq_prato_nome_restaurant'),
    ('categoria_desperdicio', 'nome', 'uq_categoria_desp_nome_restaurant'),
]


def _inspetor():
    return sa.inspect(op.get_bind())


def _uniques_de(insp, tabela, coluna):
    """Objetos únicos que cobrem exatamente esta coluna, sem repetir.

    O Postgres reporta a MESMA unique nas duas APIs de reflexão (uma constraint
    unique cria um índice implícito), então dedupa-se por nome preferindo
    tratá-la como constraint — `DROP INDEX` num índice implícito falha.
    """
    achados = {}
    for u in insp.get_unique_constraints(tabela):
        if list(u.get('column_names') or []) == [coluna] and u.get('name'):
            achados[u['name']] = 'constraint'
    for i in insp.get_indexes(tabela):
        if i.get('unique') and list(i.get('column_names') or []) == [coluna] and i.get('name'):
            achados.setdefault(i['name'], 'indice')
    return achados


def upgrade():
    insp = _inspetor()
    tabelas = set(insp.get_table_names())
    sqlite = op.get_bind().dialect.name == 'sqlite'

    for tabela, coluna, nome_novo in ALVOS:
        if tabela not in tabelas:
            continue

        antigos = _uniques_de(insp, tabela, coluna)
        ja_tem_novo = any(
            u.get('name') == nome_novo for u in insp.get_unique_constraints(tabela))

        if sqlite:
            # SQLite não altera constraint no lugar: batch recria a tabela.
            with op.batch_alter_table(tabela) as batch:
                for nome, tipo in antigos.items():
                    if tipo == 'indice':
                        batch.drop_index(nome)
                    else:
                        batch.drop_constraint(nome, type_='unique')
                if not ja_tem_novo:
                    batch.create_unique_constraint(nome_novo, [coluna, 'restaurant_id'])
            continue

        # Postgres: DDL direto, um try por objeto. Dentro de batch_alter_table
        # as operações só são emitidas no fim do bloco, então um try em volta
        # do batch não isola nada — o erro de um derruba os outros.
        for nome, tipo in antigos.items():
            try:
                if tipo == 'indice':
                    op.drop_index(nome, table_name=tabela)
                else:
                    op.drop_constraint(nome, tabela, type_='unique')
            except Exception:
                # Banco divergente: o unique pode não existir de verdade.
                pass
        if not ja_tem_novo:
            op.create_unique_constraint(nome_novo, tabela, [coluna, 'restaurant_id'])


def downgrade():
    insp = _inspetor()
    tabelas = set(insp.get_table_names())

    for tabela, coluna, nome_novo in ALVOS:
        if tabela not in tabelas:
            continue
        with op.batch_alter_table(tabela) as batch:
            try:
                batch.drop_constraint(nome_novo, type_='unique')
            except Exception:
                pass
            # Volta o unique global só se não houver duplicata (senão falharia).
            duplicado = op.get_bind().execute(sa.text(
                f'SELECT 1 FROM {tabela} GROUP BY {coluna} HAVING count(*) > 1 LIMIT 1'
            )).first()
            if not duplicado:
                batch.create_unique_constraint(f'{tabela}_{coluna}_key', [coluna])
