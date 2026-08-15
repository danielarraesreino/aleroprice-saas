"""Catálogo de modelos (layouts) do site público.

O dicionário em `app/utils/modelos.py` é o que o vendedor vê no seletor e o que
a view usa pra escolher o template. Estes testes travam as duas pontas: nenhum
modelo pode nascer sem texto de venda, e nome desconhecido nunca pode virar
`render_template` de arquivo inexistente — tem que cair no clássico.
"""
import pytest

from app.utils.modelos import (
    MODELO_PADRAO, MODELOS, arquivo_do_modelo, modelo_valido, opcoes_de_modelo,
)

NOMES = ['classico', 'craft', 'tradicional', 'autoral', 'noturno', 'brasa']


def test_os_seis_modelos_estao_no_catalogo():
    assert sorted(MODELOS) == sorted(NOMES)


@pytest.mark.parametrize('nome', NOMES)
def test_todo_modelo_tem_label_descricao_para_e_arquivo(nome):
    modelo = MODELOS[nome]
    for campo in ('label', 'descricao', 'para', 'arquivo'):
        valor = modelo.get(campo)
        assert isinstance(valor, str) and valor.strip(), f'{nome}.{campo} vazio'


@pytest.mark.parametrize('nome', NOMES)
def test_modelo_valido_aceita_os_seis(nome):
    assert modelo_valido(nome)


@pytest.mark.parametrize('lixo', ['', None, 'CLASSICO', 'boteco-ambar', 'inexistente', 'craft '])
def test_modelo_valido_rejeita_desconhecido(lixo):
    assert not modelo_valido(lixo)


def test_classico_e_o_padrao_e_aponta_pra_landing_atual():
    """A landing que já está no ar. Trocar isso troca o site de todo mundo."""
    assert MODELO_PADRAO == 'classico'
    assert MODELOS['classico']['arquivo'] == 'site/landing.html'


@pytest.mark.parametrize('nome', [n for n in NOMES if n != 'classico'])
def test_demais_modelos_moram_em_site_modelos(nome):
    assert MODELOS[nome]['arquivo'] == f'site/modelos/{nome}.html'


@pytest.mark.parametrize('lixo', ['', None, 'inexistente', 'site/../etc/passwd', 'CRAFT'])
def test_arquivo_do_modelo_cai_no_classico_com_lixo(lixo):
    assert arquivo_do_modelo(lixo) == 'site/landing.html'


@pytest.mark.parametrize('nome', NOMES)
def test_arquivo_do_modelo_devolve_o_arquivo_do_modelo(nome):
    assert arquivo_do_modelo(nome) == MODELOS[nome]['arquivo']


def test_opcoes_de_modelo_devolve_os_seis_com_texto_pro_vendedor():
    opcoes = opcoes_de_modelo()
    assert [o['valor'] for o in opcoes] == list(MODELOS)
    assert len(opcoes) == 6
    for o in opcoes:
        assert set(o) == {'valor', 'label', 'descricao', 'para'}
        assert o['para'].strip()
