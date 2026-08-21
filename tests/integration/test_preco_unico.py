"""A vitrine anuncia o mesmo preço que o sistema cobra.

Já divergiu duas vezes. A primeira, a tela de planos dizia R$ 97 e a landing
R$ 197 — resolvida centralizando em `planos.precos()`. A segunda foi mais
silenciosa: a landing passou a ler `FEIRA_PRECO` e `planos.precos()` continuou
lendo `FEIRA_PRECO_SITE`, duas envs para o mesmo número. Trocar o preço num
lugar deixava o outro para trás, e quem descobre isso é o dono do bar, na mesa,
comparando a página com o que foi falado.
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


@pytest.mark.parametrize('rota', ['/', '/cadastro'])
def test_paginas_publicas_anunciam_o_preco_que_o_sistema_cobra(
        dominio_do_produto, client, rota):
    assert precos()['site'] in _html(client, rota), (
        f'{rota} não mostra {precos()["site"]} — a vitrine e a cobrança '
        'voltaram a divergir')


def test_landing_mostra_setup_e_compra(dominio_do_produto, client):
    html = _html(client, '/')

    assert taxa_de_instalacao() in html, 'a montagem sumiu da landing'
    assert compra_do_site()['valor'] in html, 'a compra do site sumiu da landing'


def test_landing_nao_tem_preco_escrito_na_mao(dominio_do_produto, client):
    """Nenhum "R$ ..." na landing que não venha do módulo de preços.

    É o que impede a regressão de voltar por outro caminho: alguém escreve
    "R$ 197" direto no template durante uma correção de texto, e a página passa
    a prometer um número que ninguém cobra.
    """
    html = _html(client, '/')

    # A calculadora ("a conta da mesa vazia") mostra dinheiro DO BAR — consumo
    # por pessoa, quanto vale uma mesa, quanto dá no mês. São números do
    # visitante, não preço nosso, e mudam a cada toque no controle. O que este
    # teste persegue é preço do NOSSO produto digitado no template.
    inicio = html.find('id="conta"')
    if inicio != -1:
        fim = html.find('id="preco"', inicio)
        html = html[:inicio] + html[fim if fim != -1 else inicio:]

    conhecidos = {precos()['site'], precos()['pro'], taxa_de_instalacao(),
                  compra_do_site()['valor'], compra_do_site()['renovacao']}
    conhecidos = {v for v in conhecidos if v}

    # Valores dos bares (nota, preço de prato) não entram: o que se procura é
    # preço do NOSSO produto, sempre escrito como "R$ <número>".
    achados = set(re.findall(r'R\$\s?[\d.,]+(?:/ano|/mês)?', html))
    estranhos = {v for v in achados
                 if not any(v in c or c in v for c in conhecidos)}

    assert not estranhos, f'preços escritos na mão na landing: {sorted(estranhos)}'


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
