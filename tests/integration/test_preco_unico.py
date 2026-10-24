"""As páginas comerciais (/cadastro, /barao, /site-para-bar-em-campinas)
anunciam o mesmo preço que o sistema cobra, enquanto a home comunitária (/)
não exibe tabela comercial de preços nem calculadora de ROI.
"""
import re

import pytest

from app.utils.planos import compra_do_site, precos, taxa_de_instalacao


@pytest.fixture(autouse=True)
def sem_sobreposicao(monkeypatch):
    """`FEIRA_PRECO` existe pra testar discurso; aqui atrapalha a medição."""
    monkeypatch.delenv('FEIRA_PRECO', raising=False)


def _html(client, rota):
    return client.get(rota, headers={'Host': 'feiradebarao.com.br'}).get_data(as_text=True)


@pytest.fixture
def dominio_do_produto(app):
    app.config['SEPARAR_DOMINIOS'] = True
    return app


@pytest.mark.parametrize('rota', ['/cadastro', '/barao', '/site-para-bar-em-campinas'])
def test_paginas_publicas_anunciam_o_preco_que_o_sistema_cobra(
        dominio_do_produto, client, rota):
    assert precos()['site'] in _html(client, rota), (
        f'{rota} não mostra {precos()["site"]} — a vitrine e a cobrança '
        'voltaram a divergir')


def test_paginas_de_bares_mostram_setup_e_compra(dominio_do_produto, client):
    html = _html(client, '/site-para-bar-em-campinas')

    assert taxa_de_instalacao() in html, 'a montagem sumiu da página comercial'
    assert compra_do_site()['valor'] in html, 'a compra do site sumiu da página comercial'


def test_landing_comunitaria_nao_exibe_tabela_de_precos_nem_calculadora(
        dominio_do_produto, client):
    """A home (/) é o portal cultural e comunitário da Feira de Barão: não
    exibe tabela de planos (#preco), calculadora (#conta) nem cifra comercial
    de assinatura ('R$ ...')."""
    html = _html(client, '/')

    assert 'id="preco"' not in html
    assert 'id="conta"' not in html
    achados = set(re.findall(r'R\$\s?[\d.,]+(?:/ano|/mês)?', html))
    assert not achados, f'preços na home comunitária: {sorted(achados)}'


def test_sem_teste_gratis_a_pagina_nao_promete_teste(dominio_do_produto, client):
    """Com `FEIRA_DIAS_TRIAL=0`, nada de "grátis por N dias" na tela.

    Prometer teste que não existe é a reclamação que chega depois do cadastro,
    quando a pessoa já deu o e-mail.
    """
    from app.utils.planos import DIAS_DE_TRIAL
    if DIAS_DE_TRIAL > 0:
        pytest.skip('teste grátis está aberto nesta configuração')

    html = _html(client, '/cadastro')
    assert 'dias grátis' not in html
