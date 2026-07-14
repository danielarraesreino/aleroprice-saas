"""Roteamento por domínio + tema por bar; persiste a identidade do Bar da Vila.

Duas coisas acontecem aqui, e a ORDEM importa:

1. Schema: `restaurante.slug` / `restaurante.dominio` (roteamento do site público
   por Host) e `site_config.tema` (preset de paleta).

2. Dados: até agora, a identidade e o conteúdo do Bar da Vila (nome, endereço,
   WhatsApp, Instagram, cardápio, avaliações, equipe, galeria) viviam como
   CONSTANTES no código — `SITE_DEFAULTS`/`DISH_DEFAULTS`/etc em
   `app/routes/publico/views.py`. Qualquer bar sem SiteConfig herdava tudo isso,
   inclusive o telefone do dono do Bar da Vila.
   O código agora usa fallback neutro. Se esta migration NÃO gravasse a
   identidade do Bar da Vila no banco antes disso, o site dele — cliente pagante,
   no ar em bardavila.bar — ficaria em branco no deploy.

Os dados abaixo são um snapshot literal daquelas constantes. Não importamos o
módulo do app de propósito: migration tem que ser reproduzível mesmo depois de o
código mudar.

Revision ID: a1c4f7e9d2b0
Revises: 877fb41b68a1
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1c4f7e9d2b0'
down_revision = '877fb41b68a1'
branch_labels = None
depends_on = None


BARDAVILA_SLUG = 'bar-da-vila'
BARDAVILA_DOMINIO = 'bardavila.bar'

SITE = {
    'nome': 'Bar da Vila',
    'hero_linha1': 'Bar da',
    'hero_linha2': 'Vila',
    'kicker': 'VILA LEMOS · CAMPINAS–SP · DESDE SEMPRE',
    'tagline': 'Buteco de família de verdade — comida de vó, cerveja gelada e samba pra ninguém botar defeito.',
    'subline': 'COSTELINHA · CROQUETE DA BRUNA · SAMBA AO VIVO',
    'selo_estrelas': '4,9 no Google · 39 avaliações',
    'hero_foto': 'img/bar/foto-18.jpg',
    'whatsapp': '5519999779942',
    'telefone_exibicao': '(19) 99977-9942',
    'endereco': 'R. Madalena Barbosa Ferreira, 178 — Vila Lemos, Campinas–SP · 13100-486',
    'cidade_uf': 'Vila Lemos, Campinas–SP',
    'horario': 'Aberto até as 21:00 · Quarta é o dia de pico',
    'maps_query': 'Bar+da+Vila+R.+Madalena+Barbosa+Ferreira+178+Vila+Lemos+Campinas',
    'instagram_url': 'https://www.instagram.com/barda_vila178/',
    'facebook_url': 'https://www.facebook.com/p/Bar-da-VILA-61561126014944/',
    'tema': 'boteco-ambar',
}

DISHES = [
    ('Croquete da Bruna', 'Crocante por fora, macio por dentro, bem temperado — com aquela pimenta saborosa da casa. O xodó do bar.', 'img/bar/foto-5.jpg', '★ O MAIS PEDIDO', True),
    ('Costelinha', 'Costelinha com farofa e ora-pro-nóbis refogadinha. Prato que faz gente voltar sempre.', 'img/bar/foto-3.jpg', None, False),
    ('Porções pra dividir', 'Frango a passarinho, batata na hora e cerveja estupidamente gelada. O combo do fim de tarde.', 'img/bar/foto-20.jpg', None, False),
    ('Prato do dia', 'Comida caseira no capricho — arroz, feijão, o acompanhamento e aquele tempero de vó.', 'img/bar/foto-17.jpg', None, False),
]

REVIEWS = [
    ('Gerzio Vieira Junior', 'Buteco de família, extremamente acolhedor. A costelinha com farofa e ora-pro-nóbis estava maravilhosa.', 5),
    ('Rony Nunes', 'Autêntico bar raiz. Bruna e Gustavo são excelentes anfitriões. Comida de buteco típica de vó.', 5),
    ('Aline Fernandes', 'Croquete delicioso, crocante e bem temperado, pimenta muito saborosa! A carbonara é maravilhosa.', 5),
    ('Antonio Ribeiro', 'O grupo de samba que se apresenta torna o ambiente muito agradável. Cerveja, boa música e amigos.', 5),
    ('Jairo Castro', 'A melhor comida de boteco de Campinas e Região.', 5),
    ('Tia Andreia', 'Lugar familiar, comida e música boa. A Bruna é uma cozinheira de mão cheia, família abençoada!', 5),
]

TEAM = [
    ('Bruna', 'Cozinheira e anfitriã · o tempero de vó', '👩‍🍳'),
    ('Gustavo', 'Anfitrião · o samba e a resenha', '🍺'),
]

GALLERY = [18, 3, 5, 7, 12, 20, 6, 8, 17, 14, 1, 4, 9, 16, 19]


def _slugify(nome):
    import re
    import unicodedata
    t = unicodedata.normalize('NFKD', nome or '')
    t = t.encode('ascii', 'ignore').decode('ascii').lower()
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    return t[:60] or 'bar'


def _tabelas(conn):
    return set(sa.inspect(conn).get_table_names())


def upgrade():
    conn = op.get_bind()
    tabelas = _tabelas(conn)

    # --- schema -------------------------------------------------------------
    with op.batch_alter_table('restaurante') as batch:
        batch.add_column(sa.Column('slug', sa.String(length=60), nullable=True))
        batch.add_column(sa.Column('dominio', sa.String(length=120), nullable=True))
    op.create_index('ix_restaurante_slug', 'restaurante', ['slug'], unique=True)
    op.create_index('ix_restaurante_dominio', 'restaurante', ['dominio'], unique=True)

    # site_config nasceu do db.create_all() e não tem migration própria; em um
    # banco novo (testes) a tabela pode não existir ainda.
    tem_site_config = 'site_config' in tabelas
    if tem_site_config:
        with op.batch_alter_table('site_config') as batch:
            batch.add_column(sa.Column('tema', sa.String(length=30), nullable=True))
        conn.execute(sa.text("UPDATE site_config SET tema = 'boteco-ambar' WHERE tema IS NULL"))

    # --- dados --------------------------------------------------------------
    restaurantes = conn.execute(
        sa.text('SELECT id, nome FROM restaurante ORDER BY id')
    ).fetchall()
    if not restaurantes:
        return

    # slug pra todo mundo (unicidade garantida por sufixo)
    usados = set()
    for rid, nome in restaurantes:
        base = _slugify(nome)
        slug = base
        n = 2
        while slug in usados:
            slug = f'{base}-{n}'
            n += 1
        usados.add(slug)
        conn.execute(
            sa.text('UPDATE restaurante SET slug = :slug WHERE id = :id'),
            {'slug': slug, 'id': rid},
        )

    # O Bar da Vila é o tenant que a raiz `/` servia antes (o de menor id — era
    # literalmente `ORDER BY id LIMIT 1`). É ele que ganha o domínio e a
    # identidade materializada.
    bardavila_id = restaurantes[0][0]
    conn.execute(
        sa.text('UPDATE restaurante SET slug = :slug, dominio = :dom WHERE id = :id'),
        {'slug': BARDAVILA_SLUG, 'dom': BARDAVILA_DOMINIO, 'id': bardavila_id},
    )

    if not tem_site_config:
        return

    ja_tem = conn.execute(
        sa.text('SELECT id FROM site_config WHERE restaurant_id = :id'),
        {'id': bardavila_id},
    ).fetchone()

    if not ja_tem:
        cols = ', '.join(['restaurant_id'] + list(SITE.keys()))
        binds = ', '.join([':restaurant_id'] + [f':{k}' for k in SITE])
        conn.execute(
            sa.text(f'INSERT INTO site_config ({cols}) VALUES ({binds})'),
            {'restaurant_id': bardavila_id, **SITE},
        )

    def vazia(tabela):
        return conn.execute(
            sa.text(f'SELECT COUNT(*) FROM {tabela} WHERE restaurant_id = :id'),
            {'id': bardavila_id},
        ).scalar() == 0

    if 'site_dish' in tabelas and vazia('site_dish'):
        for ordem, (nome, desc, img, tag, destaque) in enumerate(DISHES):
            conn.execute(sa.text(
                'INSERT INTO site_dish (restaurant_id, nome, descricao, imagem, tag, destaque, ordem, ativo) '
                'VALUES (:r, :n, :d, :i, :t, :dq, :o, :a)'
            ), {'r': bardavila_id, 'n': nome, 'd': desc, 'i': img, 't': tag,
                'dq': destaque, 'o': ordem, 'a': True})

    if 'site_review' in tabelas and vazia('site_review'):
        for ordem, (autor, texto, estrelas) in enumerate(REVIEWS):
            conn.execute(sa.text(
                'INSERT INTO site_review (restaurant_id, autor, texto, estrelas, ordem, ativo) '
                'VALUES (:r, :a, :t, :e, :o, :at)'
            ), {'r': bardavila_id, 'a': autor, 't': texto, 'e': estrelas,
                'o': ordem, 'at': True})

    if 'site_team' in tabelas and vazia('site_team'):
        for ordem, (nome, papel, emoji) in enumerate(TEAM):
            conn.execute(sa.text(
                'INSERT INTO site_team (restaurant_id, nome, papel, emoji, ordem, ativo) '
                'VALUES (:r, :n, :p, :e, :o, :a)'
            ), {'r': bardavila_id, 'n': nome, 'p': papel, 'e': emoji,
                'o': ordem, 'a': True})

    if 'site_gallery' in tabelas and vazia('site_gallery'):
        for ordem, n in enumerate(GALLERY):
            conn.execute(sa.text(
                'INSERT INTO site_gallery (restaurant_id, imagem, legenda, ordem, ativo) '
                'VALUES (:r, :i, NULL, :o, :a)'
            ), {'r': bardavila_id, 'i': f'img/bar/foto-{n}.jpg', 'o': ordem, 'a': True})


def downgrade():
    conn = op.get_bind()
    tabelas = _tabelas(conn)

    op.drop_index('ix_restaurante_dominio', table_name='restaurante')
    op.drop_index('ix_restaurante_slug', table_name='restaurante')
    with op.batch_alter_table('restaurante') as batch:
        batch.drop_column('dominio')
        batch.drop_column('slug')

    if 'site_config' in tabelas:
        with op.batch_alter_table('site_config') as batch:
            batch.drop_column('tema')

    # As linhas de conteúdo NÃO são removidas: a partir daqui elas são os dados
    # reais do Bar da Vila, não um seed descartável.
