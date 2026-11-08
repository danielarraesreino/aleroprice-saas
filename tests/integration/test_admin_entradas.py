"""Entradas de login nas páginas públicas: rótulo único e destino /auth/login.

Portal: topo (barra e gaveta) e rodapés. Bares: rodapé "Área do lojista".
Hotsite de expositor: rodapé "Área do expositor", apontando para o domínio do produto.
"""
import re

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.scripts.seed_berga import SLUG, semear
from app.utils.modelos import MODELOS, MODELOS_ARTESAO
from app.utils.site_router import url_do_sistema

LOGIN = '/auth/login'


def _links_para_login(corpo):
    return re.findall(r'<a\b[^>]*href="([^"]*' + re.escape(LOGIN) + r')"[^>]*>(.*?)</a>', corpo, re.S)


def _rotulos(corpo):
    return [re.sub(r'<[^>]+>', '', r).strip() for _, r in _links_para_login(corpo)]


@pytest.mark.parametrize('url', ['/', '/feira', '/agenda', '/memoria', '/presentes'])
def test_topo_do_portal_tem_entrar_na_barra_e_na_gaveta(client, url):
    corpo = client.get(url).get_data(as_text=True)
    nav = re.search(r'<nav class="nav-dossie".*?</nav>', corpo, re.S).group(0)
    gaveta = re.search(r'<aside id="menu-mobile-drawer".*?</aside>', corpo, re.S).group(0)
    assert _rotulos(nav) == ['Entrar']
    assert _rotulos(gaveta) == ['Entrar']


@pytest.mark.parametrize('url', ['/', '/feira', '/agenda', '/memoria', '/presentes', '/expor', '/barao'])
def test_rodape_do_portal_tem_entrar_e_nenhum_rotulo_antigo(client, url):
    corpo = client.get(url).get_data(as_text=True)
    rodape = corpo[corpo.rindex('<footer'):]
    assert 'Entrar' in _rotulos(rodape)
    for antigo in ('Entrar no painel', 'Entrar no sistema'):
        assert antigo not in corpo


@pytest.mark.parametrize('modelo', list(MODELOS_ARTESAO))
def test_hotsite_de_expositor_tem_area_do_expositor_no_rodape(client, session, modelo):
    semear(no_ar=True)
    corpo = client.get(f'/expositor/{SLUG}?modelo={modelo}').get_data(as_text=True)
    rodape = corpo[corpo.index('<footer class="rodape"'):]
    assert f'href="{url_do_sistema()}"' in rodape
    assert 'Área do expositor' in _rotulos(rodape)


@pytest.mark.parametrize('modelo', list(MODELOS))
def test_site_de_bar_tem_area_do_lojista(client, session, modelo):
    r = Restaurante(nome='Bar Entrada', cnpj='55555555000191', slug='bar-entrada', subscription_tier='site')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar Entrada', modelo='classico'))
    session.commit()
    corpo = client.get(f'/bar/{r.slug}?modelo={modelo}').get_data(as_text=True)
    assert f'href="{url_do_sistema()}"' in corpo
    rotulos = _rotulos(corpo)
    assert 'Área do lojista' in rotulos or (modelo == 'brasa' and 'Entrar' in rotulos)
    assert not any('entrar no sistema' in r for r in rotulos)
