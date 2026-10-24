"""Contrato de design: todo modelo de site (bar e expositor) cumpre o piso.

É o gate que prende a qualidade quando há muitos tenants: modelo novo entra em
`MODELOS`/`MODELOS_ARTESAO` e passa a ser testado aqui sem editar este arquivo.
Regras vêm da skill `design-feira` (R4, R5, R7, R9, R11) e do SEO do bar.
Renderiza SEM nenhuma foto de propósito: é o caso que mais quebra.
"""
import re

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import ProdutoSite
from app.scripts.seed_berga import SLUG, semear
from app.utils.modelos import MODELOS, MODELOS_ARTESAO


def _renderiza_bar(client, session, modelo):
    r = Restaurante(nome='Bar Contrato', cnpj='44444444000194', slug='bar-contrato',
                    subscription_tier='site')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar Contrato', modelo='classico'))
    session.commit()
    resp = client.get(f'/bar/{r.slug}?modelo={modelo}')
    return resp.status_code, resp.get_data(as_text=True)


def _renderiza_artesao(client, session, modelo, com_foto=True):
    rest, _ = semear(no_ar=True)
    if not com_foto:
        cfg = SiteConfig.query.filter_by(restaurant_id=rest.id).first()
        cfg.hero_foto = cfg.logo = None
        ProdutoSite.query.filter_by(restaurant_id=rest.id).update({'imagem': None})
        session.commit()
    resp = client.get(f'/bar/{SLUG}?modelo={modelo}')
    return resp.status_code, resp.get_data(as_text=True)


CASOS = ([('bar', m, False) for m in MODELOS]
         + [('artesao', m, True) for m in MODELOS_ARTESAO]
         + [('artesao', m, False) for m in MODELOS_ARTESAO])


@pytest.fixture
def pagina(request, client, session):
    tipo, modelo, com_foto = request.param
    if tipo == 'bar':
        return (tipo, modelo, *_renderiza_bar(client, session, modelo), com_foto)
    return (tipo, modelo, *_renderiza_artesao(client, session, modelo, com_foto), com_foto)


@pytest.mark.parametrize('pagina', CASOS, indirect=True, ids=lambda c: f'{c[0]}-{c[1]}-{"foto" if c[2] else "sem-foto"}')
class TestPisoDeDesign:
    def test_renderiza(self, pagina):
        assert pagina[2] == 200

    def test_um_unico_h1(self, pagina):
        assert pagina[3].count('<h1') == 1

    def test_seo_basico(self, pagina):
        corpo = pagina[3]
        assert 'rel="canonical"' in corpo, 'falta canonical'
        assert 'property="og:title"' in corpo and 'property="og:url"' in corpo
        if pagina[4]:   # og:image só existe quando há foto de capa (decisão dos modelos)
            assert 'property="og:image"' in corpo, 'falta og:image'
        if pagina[0] == 'artesao':   # modelo de bar omite description sem dado real (decisão em seo.py)
            assert '<meta name="description"' in corpo

    def test_movimento_respeita_reduced_motion(self, pagina):
        assert 'prefers-reduced-motion' in pagina[3]

    def test_claro_e_escuro(self, pagina):
        corpo = pagina[3]
        assert 'data-theme' in corpo

    def test_sem_foto_nao_gera_imagem_quebrada(self, pagina):
        corpo = pagina[3]
        sem_lightbox = re.sub(r'<img[^>]*id="lightbox-img"[^>]*>', '', corpo)   # src vazio é do lightbox
        assert not re.search(r'src="(None|undefined|)"', sem_lightbox)
        assert not re.search(r'url\((None|undefined)\)', corpo)

    def test_sem_nome_de_tenant_fixo_no_template(self, pagina):
        # o piloto não pode vazar para outro tenant
        if pagina[0] == 'bar':
            assert 'Dona Berga' not in pagina[3]
        else:
            assert 'Bar da Vila' not in pagina[3]

    def test_previa_so_aparece_em_demo(self, pagina):
        assert 'faixa-previa' not in pagina[3]


@pytest.mark.parametrize('modelo', list(MODELOS_ARTESAO))
def test_faixa_de_previa_em_todo_modelo_de_expositor(client, session, modelo):
    rest, _ = semear(no_ar=True)
    rest.tipo_conta = 'demo'
    session.commit()
    corpo = client.get(f'/bar/{SLUG}?modelo={modelo}').get_data(as_text=True)
    assert 'faixa-previa' in corpo and 'noindex' in corpo


@pytest.mark.parametrize('modelo', list(MODELOS_ARTESAO))
def test_paridade_com_bar_novidades_e_preload_do_hero(client, session, modelo):
    """R13: o que o bar tem de head/rodapé o expositor também tem (docs 11_PARIDADE)."""
    corpo = client.get(f'/bar/{SLUG}?modelo={modelo}').get_data(as_text=True) if semear(no_ar=True) else ''
    assert 'novidades-box' in corpo and 'novidades da Feira de Barão' in corpo
    assert 'rel="preload" as="image"' in corpo
