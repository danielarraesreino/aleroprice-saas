"""Expositor (artesão) mora em /expositor/<slug>; bar segue em /bar/<slug>.
O prefixo trocado leva 301 para o certo, com a query junto."""
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.scripts.seed_berga import SLUG
from tests.integration.test_indexacao_artesao import PRODUTO, _artesao_previa, _sitemap


def _bar(session):
    r = Restaurante(nome='Bar do Largo', slug='bar-do-largo', cnpj='71000000000190')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar do Largo',
                           endereco='Rua Maria Ferraz, 10 — Barão Geraldo, Campinas - SP'))
    session.commit()
    return r


def test_artesao_abre_em_expositor(client, session):
    _artesao_previa()
    resp = client.get(f'/expositor/{SLUG}', headers={'Host': PRODUTO})
    assert resp.status_code == 200
    assert f'rel="canonical" href="https://{PRODUTO}/expositor/{SLUG}"' in resp.get_data(as_text=True)


def test_bar_slug_de_artesao_vira_301_para_expositor(client, session):
    _artesao_previa()
    resp = client.get(f'/bar/{SLUG}?modelo=atelie', headers={'Host': PRODUTO})
    assert resp.status_code == 301
    assert resp.headers['Location'] == f'/expositor/{SLUG}?modelo=atelie'


def test_bar_segue_em_bar_e_expositor_de_bar_vira_301(client, session):
    _bar(session)
    assert client.get('/bar/bar-do-largo', headers={'Host': PRODUTO}).status_code == 200
    resp = client.get('/expositor/bar-do-largo', headers={'Host': PRODUTO})
    assert resp.status_code == 301 and resp.headers['Location'] == '/bar/bar-do-largo'


def test_expositor_inexistente_da_404(client, session):
    assert client.get('/expositor/nao-existe').status_code == 404


def test_sitemap_lista_artesao_em_expositor_e_bar_em_bar(client, session):
    _artesao_previa()
    _bar(session)
    xml = _sitemap(client)
    assert f'<loc>https://{PRODUTO}/expositor/{SLUG}</loc>' in xml
    assert f'/bar/{SLUG}' not in xml
    assert f'<loc>https://{PRODUTO}/bar/bar-do-largo</loc>' in xml


def test_feira_linka_o_expositor_por_expositor(client, session):
    _artesao_previa()
    html = client.get('/feira', headers={'Host': PRODUTO}).get_data(as_text=True)
    assert f'/expositor/{SLUG}' in html and f'/bar/{SLUG}' not in html
