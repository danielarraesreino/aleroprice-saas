"""O sitemap é a lista do que pedimos pro Google indexar — e ela é por domínio.

Dois erros seriam caros e silenciosos. Primeiro: listar a prévia comercial. A
prévia é montada por nós a partir de dado público, sem o dono saber, e vem com
`noindex`; pedir indexação dela seria entregar a lista de prospecção e ainda
competir no Google com o negócio real da pessoa. Segundo: servir a lista inteira
de clientes no domínio de um cliente — bardavila.bar não hospeda o catálogo de
concorrentes do dono.
"""
import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig

PRODUTO = 'feiradebarao.com.br'
CLIENTE = 'bardavila.bar'


@pytest.fixture(autouse=True)
def dominio_do_produto(monkeypatch):
    monkeypatch.setenv('DOMINIO_PRODUTO', PRODUTO)


@pytest.fixture
def bares(session):
    """Um cliente com domínio, um cliente sem (com endereço), um cadastro pela
    metade (sem endereço), uma prévia e um desligado."""
    com_dominio = Restaurante(nome='Bar da Vila', slug='bar-da-vila',
                              dominio=CLIENTE, tipo_conta='cliente')
    sem_dominio = Restaurante(nome='Bar do Zé', slug='bar-do-ze',
                              tipo_conta='cliente')
    previa = Restaurante(nome='Tatu Bola', slug='tatu-bola', tipo_conta='demo')
    desligado = Restaurante(nome='Bar Fechado', slug='bar-fechado',
                            tipo_conta='cliente', ativo=False)
    pela_metade = Restaurante(nome='Demo Avaliação', slug='demo-avaliacao',
                              tipo_conta='cliente')
    session.add_all([com_dominio, sem_dominio, previa, desligado, pela_metade])
    session.commit()
    session.add_all([
        SiteConfig(restaurant_id=com_dominio.id, nome='Bar da Vila',
                   endereco='R. Madalena Barbosa Ferreira, 178 — Vila Lemos, Campinas–SP'),
        SiteConfig(restaurant_id=sem_dominio.id, nome='Bar do Zé',
                   endereco='Av. Santa Isabel, 57 — Barão Geraldo, Campinas - SP'),
    ])
    session.commit()
    return {'com_dominio': com_dominio, 'sem_dominio': sem_dominio,
            'previa': previa, 'desligado': desligado, 'pela_metade': pela_metade}


def corpo(client, host):
    resp = client.get('/sitemap.xml', headers={'Host': host})
    assert resp.status_code == 200
    assert 'xml' in resp.headers['Content-Type']
    return resp.get_data(as_text=True)


def test_dominio_do_produto_lista_a_venda_e_os_bares_do_portal(client, bares):
    xml = corpo(client, PRODUTO)

    assert f'<loc>https://{PRODUTO}/</loc>' in xml
    assert f'<loc>https://{PRODUTO}/bar/bar-do-ze</loc>' in xml


def test_bar_com_dominio_proprio_fica_fora_do_sitemap_do_portal(client, bares):
    """URL de outro host o Google descarta, e o bar com domínio próprio não é
    barraca da feira: ele tem o sitemap dele."""
    xml = corpo(client, PRODUTO)
    assert CLIENTE not in xml
    assert 'bar-da-vila' not in xml


def test_cadastro_sem_endereco_fica_fora_do_sitemap(client, bares):
    """Conta de teste ou cadastro pela metade: a página sairia vazia."""
    assert 'demo-avaliacao' not in corpo(client, PRODUTO)


def test_cardapio_entra_no_sitemap_quando_tem_prato(client, bares, session):
    from app.models.modelo_sitecontent import DishCard
    session.add(DishCard(restaurant_id=bares['com_dominio'].id, nome='Torresmo'))
    session.commit()
    xml = corpo(client, CLIENTE)
    assert f'<loc>https://{CLIENTE}/bar/bar-da-vila/cardapio</loc>' in xml
    assert '/bar/bar-do-ze/cardapio' not in corpo(client, PRODUTO)


def test_previa_comercial_nunca_entra_no_sitemap(client, bares):
    """Ela é noindex: pedir indexação do que se marcou como não-indexável é
    contradição que o Search Console reporta como erro."""
    assert 'tatu-bola' not in corpo(client, PRODUTO)


def test_tenant_desligado_nao_entra_no_sitemap(client, bares):
    assert 'bar-fechado' not in corpo(client, PRODUTO)


def test_no_dominio_do_bar_o_sitemap_fala_so_daquele_bar(client, bares):
    xml = corpo(client, CLIENTE)

    assert f'<loc>https://{CLIENTE}/</loc>' in xml
    assert 'bar-do-ze' not in xml
    assert f'https://{PRODUTO}/</loc>' not in xml


def test_bar_com_dominio_proprio_e_listado_uma_vez_so(client, bares):
    """Um bar responde em três endereços; o Google precisa de um canônico só,
    senão o mesmo conteúdo compete consigo mesmo."""
    xml = corpo(client, CLIENTE)
    assert f'{PRODUTO}/bar/bar-da-vila' not in xml   # nunca pelo slug do portal
    assert xml.count(f'<loc>https://{CLIENTE}/</loc>') == 1


def test_lastmod_sai_da_data_real_de_edicao(client, bares):
    cfg = SiteConfig.query.filter_by(restaurant_id=bares['com_dominio'].id).first()
    xml = corpo(client, CLIENTE)
    assert f'<lastmod>{cfg.data_atualizacao.date().isoformat()}</lastmod>' in xml


def test_bar_sem_data_de_edicao_sai_sem_lastmod(client, bares, session):
    """Data inventada é o oposto do sinal de frescor que se quer dar."""
    cfg = SiteConfig.query.filter_by(restaurant_id=bares['sem_dominio'].id).first()
    session.execute(SiteConfig.__table__.update()
                    .where(SiteConfig.id == cfg.id).values(data_atualizacao=None))
    session.commit()
    xml = corpo(client, PRODUTO)
    trecho = xml.split('bar-do-ze')[1].split('</url>')[0]
    assert 'lastmod' not in trecho


def test_robots_aponta_para_o_sitemap_do_proprio_dominio(client, bares):
    resp = client.get('/robots.txt', headers={'Host': CLIENTE})
    assert f'Sitemap: https://{CLIENTE}/sitemap.xml' in resp.get_data(as_text=True)


def test_sitemap_responde_no_dominio_do_bar_sem_redirecionar(client, bares,
                                                             monkeypatch):
    """Se o sitemap fosse redirecionado pro domínio do produto, o Google o
    descartaria: sitemap de outro host não vale pro host que o referenciou."""
    monkeypatch.setenv('SEPARAR_DOMINIOS', '1')
    resp = client.get('/sitemap.xml', headers={'Host': CLIENTE})
    assert resp.status_code == 200


def test_bar_com_dominio_proprio_sai_do_portal_com_301(client, bares):
    """O Bar da Vila é cliente da Vila Lemos, não barraca da feira: no portal,
    o /bar/<slug> dele leva para o domínio dele."""
    resp = client.get('/bar/bar-da-vila', headers={'Host': PRODUTO})
    assert resp.status_code == 301
    assert resp.headers['Location'] == f'https://{CLIENTE}/'


def test_bar_com_dominio_proprio_abre_no_proprio_dominio(client, bares):
    resp = client.get('/bar/bar-da-vila', headers={'Host': CLIENTE})
    assert resp.status_code == 200


def test_titulo_do_bar_leva_o_bairro(client, bares):
    html = client.get('/', headers={'Host': CLIENTE}).get_data(as_text=True)
    titulo = html.split('<title>')[1].split('</title>')[0]
    assert 'Vila Lemos' in titulo


def test_llms_do_portal_nao_lista_bar_de_dominio_proprio(client, bares):
    texto = client.get('/llms.txt', headers={'Host': PRODUTO}).get_data(as_text=True)
    assert 'Bar da Vila' not in texto
    assert 'Demo Avaliação' not in texto
    assert 'Bar do Zé' in texto


def test_llms_do_bar_nao_carimba_barao_geraldo(client, bares):
    texto = client.get('/llms.txt', headers={'Host': CLIENTE}).get_data(as_text=True)
    assert 'Barão Geraldo' not in texto.splitlines()[0]


def test_sitemap_do_portal_tem_a_pagina_de_venda(client, bares):
    xml = client.get('/sitemap.xml', headers={'Host': PRODUTO}).get_data(as_text=True)
    assert f'https://{PRODUTO}/site-para-bar-em-campinas' in xml
