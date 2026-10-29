"""Plano de Natal 2026: calculadora da mesa vazia, preço novo do bar e as
correções da auditoria de design de 29/10/2026."""
import pathlib
import re

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.utils.modelos import MODELOS
from app.utils.planos import precos, precos_expositor

SITE = pathlib.Path(__file__).resolve().parents[2] / 'app' / 'templates' / 'site'


@pytest.fixture(autouse=True)
def sem_sobreposicao(monkeypatch):
    for env in ('FEIRA_PRECO', 'FEIRA_PRECO_SITE', 'FEIRA_PRECO_SITE_ANUAL',
                'FEIRA_PRECO_SITE_ANUAL_MES', 'FEIRA_PRECO_FICHA_GOOGLE'):
        monkeypatch.delenv(env, raising=False)


def test_preco_do_bar_aprovado():
    p = precos()
    assert (p['site'], p['site_anual'], p['site_anual_mes'], p['ficha_google']) == (
        'R$ 97', 'R$ 948', 'R$ 79', 'R$ 197')


def test_pagina_do_bar_tem_calculadora_ao_lado_do_preco(client):
    html = client.get('/site-para-bar-em-campinas').get_data(as_text=True)
    assert 'data-mesa-vazia' in html and 'por mês perdidos' in html
    assert f'data-preco="{precos()["site"]}"' in html
    # sem JS, a conta do exemplo já vem feita: 2 mesas x 4 pessoas x R$ 60 x 4 noites
    assert 'R$ 1.920,00' in html
    # só cliente: a calculadora não posta nada
    trecho = html.split('data-mesa-vazia', 1)[1].split('</script>', 1)[0]
    assert '<form' not in trecho and 'fetch(' not in trecho
    assert precos()['ficha_google'] in html


def test_expor_mostra_preco_e_previa_antes_do_resto(client):
    html = client.get('/expor').get_data(as_text=True)
    hero = html.split('<header class="hero">', 1)[1].split('</header>', 1)[0]
    exp = precos_expositor()
    assert exp['anual_mes'] in hero and exp['mensal'] in hero
    assert 'Peça sua prévia grátis' in hero


@pytest.mark.parametrize('modelo', MODELOS)
def test_conteudo_nao_nasce_escondido_pela_rolagem(client, session, modelo):
    """Captura, prévia de link e robô de busca viam a página vazia: o estado
    escondido do scroll-reveal não pode existir no CSS, só na animação."""
    r = Restaurante(nome='Bar Rolagem', cnpj='44444444000195', slug='bar-rolagem',
                    subscription_tier='site')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar Rolagem', modelo='classico'))
    session.commit()
    html = client.get(f'/bar/{r.slug}?modelo={modelo}').get_data(as_text=True)
    escondido = re.compile(
        r'\.(?:js|com-js|js-anim) \.(?:rev|revelar|surge|rv|reveal)\{opacity:0')
    assert not escondido.search(html), f'{modelo}: bloco nasce com opacity:0'


def test_brasa_sem_foto_nao_mostra_letra_gigante():
    src = (SITE / 'modelos' / 'brasa.html').read_text()
    assert 'sem-foto' not in src and "d.nome[0]|upper" not in src


def test_titulo_do_noturno_quebra_so_entre_palavras():
    src = (SITE / 'modelos' / 'noturno.html').read_text()
    bloco = src.split('.nome-hero{', 1)[1].split('}', 1)[0]
    assert 'overflow-wrap:normal' in bloco


def test_vitrine_ficticia_avisa_modelo_de_demonstracao(client, session):
    r = Restaurante(nome='Tap Teste', cnpj='44444444000196', slug='vitrine-tap-teste',
                    tipo_conta='demo', demo_fonte='vitrine-da-campanha')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Tap Teste', modelo='craft'))
    session.commit()
    html = client.get(f'/bar/{r.slug}').get_data(as_text=True)
    assert 'Modelo de demonstração' in html
    assert 'class="selo-exemplo"' not in html
    assert 'Rua da Demonstração' not in html


def test_leads_nao_tem_rua_da_demonstracao():
    leads = pathlib.Path(__file__).resolve().parents[2] / 'app' / 'data' / 'leads'
    for f in leads.glob('*.yml'):
        assert 'Rua da Demonstração' not in f.read_text(), f.name
