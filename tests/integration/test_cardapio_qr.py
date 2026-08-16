"""Cardápio QR: da mesa do bar até a folha que o vendedor imprime.

São três peças que só valem juntas — a página `/bar/<slug>/cardapio`, o QR que
aponta pra ela e o papel que leva esse QR pra mesa. O que este arquivo protege,
em uma frase: **o quadrado preto colado na mesa tem que abrir um cardápio de
verdade**.

Daí o formato dos testes. QR que abre 404 (bar sem prato), QR trocado com o do
site, prévia comercial indexada como se fosse o cardápio oficial da casa e
"R$ 0,00" num prato sem preço são todos o mesmo tipo de falha: o cliente já
está sentado, com o celular na mão, e a página não entrega o que o adesivo
prometeu.
"""
import json
import re
from decimal import Decimal

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import DishCard
from app.models.usuario import Usuario


def _bar(session, *, slug, nome, demo=False, pratos=(), **cfg_extra):
    r = Restaurante(nome=nome, slug=slug,
                    tipo_conta='demo' if demo else 'cliente')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome=nome, vibe='boteco',
                           whatsapp='5519911110000', **cfg_extra))
    for i, prato in enumerate(pratos):
        session.add(DishCard(restaurant_id=r.id, ordem=i,
                             ativo=prato.pop('ativo', True), **prato))
    session.commit()
    return r


def _json_ld(corpo):
    """Os grafos JSON-LD da página, já desserializados."""
    achados = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', corpo, re.S)
    return [json.loads(t.replace('\\u003c', '<').replace('\\u003e', '>')
                       .replace('\\u0026', '&')) for t in achados]


def _no(grafo, tipo):
    return next(n for n in grafo['@graph'] if n['@type'] == tipo)


@pytest.fixture
def bar_com_cardapio(session):
    return _bar(session, slug='bar-do-qr', nome='Bar do QR', pratos=[
        {'nome': 'Costela na brasa', 'descricao': 'Oito horas de fogo.',
         'imagem': 'img/bar/costela.jpg', 'tag': '★ O MAIS PEDIDO',
         'destaque': True, 'preco': Decimal('62.00')},
        {'nome': 'Bolinho de feijoada', 'descricao': 'Seis unidades.',
         'preco': Decimal('28.50')},
    ])


# ------------------------------------------------------------------ a página

def test_cardapio_mostra_os_pratos_do_bar(client, bar_com_cardapio):
    resp = client.get('/bar/bar-do-qr/cardapio')
    corpo = resp.get_data(as_text=True)

    assert resp.status_code == 200
    for trecho in ('Bar do QR', 'Costela na brasa', 'Oito horas de fogo.',
                   'Bolinho de feijoada', 'img/bar/costela.jpg'):
        assert trecho in corpo, f'sumiu do cardápio: {trecho}'
    # Preço em real, com vírgula — quem lê está na mesa, não no Search Console.
    assert 'R$ 62,00' in corpo
    assert 'R$ 28,50' in corpo


def test_cardapio_e_publico(client, bar_com_cardapio):
    """Sem login: quem senta na mesa não tem conta em lugar nenhum."""
    resp = client.get('/bar/bar-do-qr/cardapio', follow_redirects=False)
    assert resp.status_code == 200


def test_um_h1_so(client, bar_com_cardapio):
    corpo = client.get('/bar/bar-do-qr/cardapio').get_data(as_text=True)
    assert len(re.findall(r'<h1[ >]', corpo)) == 1


def test_bar_sem_prato_nao_tem_cardapio(client, session):
    """404, e não uma página de cardápio vazia.

    Título de cardápio com nada embaixo é a versão de mesa da seção órfã: o
    cliente já está sentado esperando ler alguma coisa.
    """
    _bar(session, slug='bar-sem-prato', nome='Bar Sem Prato')

    assert client.get('/bar/bar-sem-prato/cardapio').status_code == 404


def test_prato_desativado_nao_conta_como_cardapio(client, session):
    """`ativo=False` é o dono tirando o item do ar — não pode segurar a página
    de pé sozinho, senão o QR abre um cardápio em branco."""
    _bar(session, slug='bar-desligado', nome='Bar Desligado', pratos=[
        {'nome': 'Prato fora de linha', 'ativo': False},
    ])

    assert client.get('/bar/bar-desligado/cardapio').status_code == 404


def test_bar_inexistente_da_404(client):
    assert client.get('/bar/nao-existe/cardapio').status_code == 404


def test_prato_sem_preco_nao_anuncia_preco(client, session):
    """`moeda_br` devolve "R$ 0,00" pra None. Sem o guard no template, o bar
    passa a oferecer comida de graça no cardápio da mesa."""
    _bar(session, slug='bar-sem-preco', nome='Bar Sem Preço', pratos=[
        {'nome': 'Porção do dia', 'preco': None},
    ])

    corpo = client.get('/bar/bar-sem-preco/cardapio').get_data(as_text=True)

    assert 'Porção do dia' in corpo
    assert 'R$ 0,00' not in corpo


def test_cardapio_de_um_bloco_so_nao_ganha_titulo(client, session):
    """Sem destaque nenhum não há dois blocos — e cabeçalho de grupo sem par é
    categoria inventada em cima do cardápio do dono."""
    _bar(session, slug='bar-liso', nome='Bar Liso', pratos=[
        {'nome': 'Pastel de carne'}, {'nome': 'Pastel de queijo'},
    ])

    corpo = client.get('/bar/bar-liso/cardapio').get_data(as_text=True)

    assert 'Destaques da casa' not in corpo
    assert 'Também na cozinha' not in corpo


def test_destaque_e_resto_viram_dois_blocos(client, bar_com_cardapio):
    corpo = client.get('/bar/bar-do-qr/cardapio').get_data(as_text=True)

    assert 'Destaques da casa' in corpo
    assert 'Também na cozinha' in corpo
    # O destaque vem primeiro: é o que a casa quer que se leia antes.
    assert corpo.index('Costela na brasa') < corpo.index('Bolinho de feijoada')


def test_tema_do_bar_pinta_o_cardapio(client, session):
    """O cardápio é do bar, não do produto: mesma paleta e mesmo claro/escuro
    que o dono aprovou na landing."""
    _bar(session, slug='bar-neon', nome='Bar Neon', tema='neon-noite',
         tema_modo='claro', pratos=[{'nome': 'Burger da casa'}])

    corpo = client.get('/bar/bar-neon/cardapio').get_data(as_text=True)

    assert 'data-theme="light"' in corpo
    assert '#ff2e88' in corpo, 'a paleta do tema não foi injetada'


# ------------------------------------------------------------------- prévia

def test_previa_nao_indexa_e_avisa(client, session):
    _bar(session, slug='bar-previa', nome='Bar Prévia', demo=True,
         pratos=[{'nome': 'Torresmo'}])

    corpo = client.get('/bar/bar-previa/cardapio').get_data(as_text=True)

    assert 'noindex' in corpo, 'prévia do cardápio seria indexada'
    assert 'Prévia não oficial' in corpo, 'prévia não se declara prévia'


def test_cliente_nao_e_marcado_como_previa(client, bar_com_cardapio):
    corpo = client.get('/bar/bar-do-qr/cardapio').get_data(as_text=True)

    assert 'noindex' not in corpo, 'sumiu com o cardápio do cliente no Google'
    assert 'Prévia não oficial' not in corpo


# ------------------------------------------------------------------ JSON-LD

def test_menu_da_landing_aponta_pra_pagina_do_cardapio(client, bar_com_cardapio):
    """`hasMenu` levando a um cardápio em HTML é o que o schema.org pede — e
    agora existe um."""
    corpo = client.get('/bar/bar-do-qr').get_data(as_text=True)

    cardapio = _no(_json_ld(corpo)[0], 'Menu')
    assert cardapio['url'].endswith('/bar/bar-do-qr/cardapio')
    assert cardapio['url'].startswith('https://')


def test_cardapio_publica_o_mesmo_menu_da_landing(client, bar_com_cardapio):
    """Mesmo `@id` nas duas páginas: um cardápio, uma entidade."""
    da_landing = _no(_json_ld(client.get('/bar/bar-do-qr').get_data(as_text=True))[0], 'Menu')
    da_pagina = _no(_json_ld(client.get('/bar/bar-do-qr/cardapio').get_data(as_text=True))[0], 'Menu')

    assert da_pagina['@id'] == da_landing['@id']
    assert da_pagina['url'] == da_landing['url']
    assert [i['name'] for i in da_pagina['hasMenuItem']] == [
        'Costela na brasa', 'Bolinho de feijoada']


def test_menu_sem_pagina_de_cardapio_volta_pra_ancora():
    """Bar antigo, sem slug, não tem página de cardápio — e `Menu.url` não pode
    apontar pra uma URL que ninguém registrou. Sobra a âncora da landing, que é
    o que sempre houve."""
    from app.utils import seo

    no = seo.menu_schema('Bar Velho', [{'nome': 'Coxinha'}],
                         'https://feiradebarao.com.br/s/7')

    assert no['url'] == 'https://feiradebarao.com.br/s/7#cardapio'


def test_sem_prato_nao_ha_no_de_cardapio():
    from app.utils import seo

    assert seo.menu_schema('Bar Vazio', [], 'https://x.com/bar/y') is None
    assert seo.cardapio_estruturado(None, {'nome': 'Bar Vazio'}, [],
                                    'https://x.com/bar/y') is None


def test_url_do_cardapio_acompanha_o_dominio_do_bar(session):
    """Quem tem domínio próprio lê o cardápio no endereço do bar, não no do
    produto — é o endereço que ele paga pra ser dele."""
    from app.utils.site_router import url_do_cardapio

    r = Restaurante(nome='Bar da Vila', slug='bar-da-vila', dominio='bardavila.bar')

    assert url_do_cardapio(r) == 'https://bardavila.bar/bar/bar-da-vila/cardapio'
    assert url_do_cardapio(Restaurante(nome='Sem Slug')) is None
    assert url_do_cardapio(None) is None


def test_preco_no_grafo_sai_com_ponto(client, bar_com_cardapio):
    grafo = _json_ld(client.get('/bar/bar-do-qr/cardapio').get_data(as_text=True))[0]
    item = _no(grafo, 'Menu')['hasMenuItem'][0]

    assert item['offers'] == {'@type': 'Offer', 'price': '62.00',
                              'priceCurrency': 'BRL'}


# ------------------------------------------------------- QR e folha de mesa

@pytest.fixture
def operador(session):
    """O primeiro tenant é o operador da campanha — critério de `e_operador`."""
    rest = Restaurante(nome='Alero (operador)', slug='alero-qr')
    session.add(rest)
    session.commit()
    usuario = Usuario(nome='Vendedor', email='vendedor@alero-qr.com',
                      senha='segredo123', tipo='admin', restaurant_id=rest.id)
    session.add(usuario)
    session.commit()
    return usuario


def entrar(client, email='vendedor@alero-qr.com', senha='segredo123'):
    return client.post('/auth/login', data={'email': email, 'senha': senha})


def test_qr_do_cardapio_responde_svg(client, operador, bar_com_cardapio):
    entrar(client)

    resp = client.get('/campo/bar-do-qr/qr-cardapio.svg')

    assert resp.status_code == 200
    assert resp.mimetype == 'image/svg+xml'
    # Documento SVG de verdade: sem `xmlns` o navegador não renderiza o
    # arquivo servido, e a folha da mesa sai com o quadrado vazio.
    assert b'<svg xmlns="http://www.w3.org/2000/svg"' in resp.data


def test_os_dois_qrs_levam_a_lugares_diferentes(client, operador, bar_com_cardapio):
    """Um é pra divulgar (o site), o outro pra colar na mesa (o cardápio).
    Iguais, seria um dos dois no endereço errado."""
    entrar(client)

    do_site = client.get('/campo/bar-do-qr/qr.svg').data
    do_cardapio = client.get('/campo/bar-do-qr/qr-cardapio.svg').data

    assert do_site != do_cardapio


def test_folha_de_mesa_traz_o_qr_e_a_chamada(client, operador, bar_com_cardapio):
    entrar(client)

    resp = client.get('/campo/bar-do-qr/qr-mesa')
    corpo = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert 'Bar do QR' in corpo
    assert 'Cardápio' in corpo
    assert 'Aponte a câmera' in corpo
    assert '/campo/bar-do-qr/qr-cardapio.svg' in corpo
    assert '@media print' in corpo, 'a folha não sabe se comportar no papel'
    assert '/bar/bar-do-qr/cardapio' in corpo, 'falta o endereço por extenso'


def test_folha_de_mesa_avisa_quando_nao_ha_o_que_imprimir(client, operador, session):
    """Bar sem prato: o QR abriria 404 no meio da mesa."""
    _bar(session, slug='bar-vazio-qr', nome='Bar Vazio QR')
    entrar(client)

    corpo = client.get('/campo/bar-vazio-qr/qr-mesa').get_data(as_text=True)

    assert 'Ainda não há prato cadastrado' in corpo


def test_folha_de_mesa_e_404_pra_quem_nao_e_operador(client, session,
                                                     operador, bar_com_cardapio):
    """Mesma regra do resto do Modo Campo: painel interno não se anuncia."""
    session.add(Usuario(nome='Dono', email='dono@bardoqr.com', senha='segredo123',
                        tipo='admin', restaurant_id=bar_com_cardapio.id))
    session.commit()

    entrar(client, 'dono@bardoqr.com')

    assert client.get('/campo/bar-do-qr/qr-mesa').status_code == 404
    assert client.get('/campo/bar-do-qr/qr-cardapio.svg').status_code == 404


def test_campo_oferece_os_dois_qrs_rotulados(client, operador, bar_com_cardapio):
    """Quadrados pretos idênticos: sem rótulo, o vendedor cola o errado."""
    entrar(client)

    corpo = client.get('/campo/bar-do-qr').get_data(as_text=True)

    assert '/campo/bar-do-qr/qr.svg' in corpo
    assert '/campo/bar-do-qr/qr-cardapio.svg' in corpo
    assert 'pra divulgar' in corpo
    assert 'pra colar na mesa' in corpo
    assert '/campo/bar-do-qr/qr-mesa' in corpo


def test_campo_nao_oferece_qr_de_cardapio_vazio(client, operador, session):
    _bar(session, slug='bar-nada', nome='Bar Nada')
    entrar(client)

    corpo = client.get('/campo/bar-nada').get_data(as_text=True)

    assert '/campo/bar-nada/qr-cardapio.svg' not in corpo
    assert '/campo/bar-nada/qr-mesa' not in corpo
    assert 'Cadastre um prato' in corpo
