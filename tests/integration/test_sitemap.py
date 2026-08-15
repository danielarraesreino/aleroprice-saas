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
    """Um cliente com domínio, um cliente sem, uma prévia e um desligado."""
    com_dominio = Restaurante(nome='Bar da Vila', slug='bar-da-vila',
                              dominio=CLIENTE, tipo_conta='cliente')
    sem_dominio = Restaurante(nome='Bar do Zé', slug='bar-do-ze',
                              tipo_conta='cliente')
    previa = Restaurante(nome='Tatu Bola', slug='tatu-bola', tipo_conta='demo')
    desligado = Restaurante(nome='Bar Fechado', slug='bar-fechado',
                            tipo_conta='cliente', ativo=False)
    session.add_all([com_dominio, sem_dominio, previa, desligado])
    session.commit()
    session.add(SiteConfig(restaurant_id=com_dominio.id, nome='Bar da Vila'))
    session.commit()
    return {'com_dominio': com_dominio, 'sem_dominio': sem_dominio,
            'previa': previa, 'desligado': desligado}


def corpo(client, host):
    resp = client.get('/sitemap.xml', headers={'Host': host})
    assert resp.status_code == 200
    assert 'xml' in resp.headers['Content-Type']
    return resp.get_data(as_text=True)


def test_dominio_do_produto_lista_a_venda_e_todos_os_clientes(client, bares):
    xml = corpo(client, PRODUTO)

    assert f'<loc>https://{PRODUTO}/</loc>' in xml
    assert f'<loc>https://{CLIENTE}/</loc>' in xml
    assert f'<loc>https://{PRODUTO}/bar/bar-do-ze</loc>' in xml


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
    xml = corpo(client, PRODUTO)
    assert xml.count('bar-da-vila') == 0        # nunca pelo slug
    assert xml.count(f'https://{CLIENTE}/') == 1


def test_lastmod_sai_da_data_real_de_edicao(client, bares):
    cfg = SiteConfig.query.filter_by(restaurant_id=bares['com_dominio'].id).first()
    xml = corpo(client, CLIENTE)
    assert f'<lastmod>{cfg.data_atualizacao.date().isoformat()}</lastmod>' in xml


def test_bar_sem_site_config_sai_sem_lastmod(client, bares):
    """Data inventada é o oposto do sinal de frescor que se quer dar."""
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
