"""Conteúdo do site público do Bar da Vila (SiteConfig + pratos, avaliações,
equipe, galeria).

Isto normalmente é gravado pela migration `a1c4f7e9d2b0`. Em produção, onde o
schema veio de `db.create_all()` e as migrations Alembic não rodaram, esse
conteúdo nunca entrou no banco — e como o código passou a ler o site do banco
(fallback neutro), a landing do Bar da Vila ficava sem pratos/endereço/reviews.

Este seed repõe exatamente o mesmo snapshot, de forma idempotente (só insere o
que estiver faltando). Rodável isolado e chamado pelo /bootstrap-demo.

    python -m app.scripts.seed_site_bardavila
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app
from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import DishCard, GalleryItem, Review, TeamMember

SLUG = 'bar-da-vila'

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
    'vibe': 'boteco',
    # Estes três eram texto fixo no template e apareciam no site de todo mundo.
    # Agora são dados deste bar — sem eles, o bloco correspondente some.
    'descritor': 'Buteco de família em Campinas',
    'nota_google': '4,9',
    'qtd_avaliacoes': 39,
    'servicos': 'Refeição no local · Drive-through',
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


def seed(slug=SLUG):
    rest = Restaurante.query.filter_by(slug=slug).first()
    if rest is None:
        print(f'ERRO: nenhum restaurante com slug "{slug}".')
        return 1
    rid = rest.id
    print(f'Tenant: {rest.nome} (id={rid})')

    cfg = SiteConfig.query.filter_by(restaurant_id=rid).first()
    if cfg is None:
        db.session.add(SiteConfig(restaurant_id=rid, **SITE))
        print('  site_config: criado')
    else:
        # Preenche só o que estiver vazio — não sobrescreve edição do dono.
        preenchidos = 0
        for campo, valor in SITE.items():
            if not getattr(cfg, campo, None):
                setattr(cfg, campo, valor)
                preenchidos += 1
        print(f'  site_config: existia, {preenchidos} campos vazios preenchidos')

    def repor(modelo, rows, construir, rotulo):
        if modelo.query.filter_by(restaurant_id=rid).count() > 0:
            print(f'  {rotulo}: já tinha, mantido')
            return
        for ordem, row in enumerate(rows):
            db.session.add(construir(ordem, row))
        print(f'  {rotulo}: {len(rows)} inseridos')

    repor(DishCard, DISHES, lambda o, r: DishCard(
        restaurant_id=rid, nome=r[0], descricao=r[1], imagem=r[2],
        tag=r[3], destaque=r[4], ordem=o, ativo=True), 'pratos')
    repor(Review, REVIEWS, lambda o, r: Review(
        restaurant_id=rid, autor=r[0], texto=r[1], estrelas=r[2],
        ordem=o, ativo=True), 'avaliações')
    repor(TeamMember, TEAM, lambda o, r: TeamMember(
        restaurant_id=rid, nome=r[0], papel=r[1], emoji=r[2],
        ordem=o, ativo=True), 'equipe')
    repor(GalleryItem, GALLERY, lambda o, n: GalleryItem(
        restaurant_id=rid, imagem=f'img/bar/foto-{n}.jpg', ordem=o, ativo=True),
        'galeria')

    db.session.commit()
    print('Pronto. Conteúdo do site do Bar da Vila no ar.')
    return 0


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        sys.exit(seed())
