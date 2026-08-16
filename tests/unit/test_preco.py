"""O preço entra por dois formulários e sai por dois canais — e é o mesmo número.

Entra em `/conteudo/cardapio` (dono, sentado) e no Modo Campo (vendedor, de pé,
no celular). Sai como `R$ 18,50` na tela e como `"price": "18.50"` no JSON-LD.
Se cada ponta tiver a sua própria interpretação de "18,50", o bar anuncia um
preço pro cliente e outro pro Google — e quem apanha é o bar.

Por isso existe um juiz só, `ler_moeda`, e é ele que estes testes cercam. A
regra dele é a mesma regra de ouro de `app/utils/seo.py`: **o que não é preço
não vira preço**. Vazio, zero, negativo e lixo devolvem None, nunca 0 — porque
`R$ 0,00` num cardápio é um preço anunciado, não a ausência de um.
"""
from decimal import Decimal

import pytest

from app.utils.formatacao_br import formatar_moeda, ler_moeda
from app.utils.seo import _preco_schema


# ------------------------------------------------- os três jeitos de digitar

@pytest.mark.parametrize('digitado', ['18,50', 'R$ 18,50', '18.50', 'R$18,50',
                                      ' 18,50 ', 'R$\xa018,50', '18,5'])
def test_o_vendedor_pode_digitar_do_jeito_dele(digitado):
    """Os formatos vieram do celular: com e sem 'R$', com vírgula e com ponto,
    com o espaço duro que o teclado do iOS enfia depois do cifrão."""
    assert ler_moeda(digitado) == Decimal('18.50'), digitado


def test_inteiro_sem_centavo_vira_preco_cheio():
    """"18" é dezoito reais, não dezoito centavos."""
    assert ler_moeda('18') == Decimal('18.00')
    assert ler_moeda('R$ 18') == Decimal('18.00')


def test_ponto_de_milhar_nao_vira_centavo():
    """Em BR o ponto separa milhar. Só grupo de 3 dígitos é milhar — "18.5"
    continua sendo dezoito e cinquenta, não 185."""
    assert ler_moeda('1.234,56') == Decimal('1234.56')
    assert ler_moeda('1.234') == Decimal('1234.00')
    assert ler_moeda('18.5') == Decimal('18.50')


def test_notacao_americana_nao_e_adivinhada():
    """"1,234.56" com ponto depois da vírgula não é jeito brasileiro de
    escrever. Chutar ali devolveria R$ 1,23 num prato de R$ 1.234,56 — e um
    preço errado calado é pior que um campo vazio, que o dono vê e corrige."""
    assert ler_moeda('1,234.56') is None
    assert ler_moeda('1.234,56') == Decimal('1234.56')   # o BR continua valendo


def test_numero_ja_pronto_passa_direto():
    """O valor que volta do banco é Decimal e precisa atravessar sem estrago."""
    assert ler_moeda(Decimal('18.50')) == Decimal('18.50')
    assert ler_moeda(18.5) == Decimal('18.50')
    assert ler_moeda(12) == Decimal('12.00')


# --------------------------------------------- o que NÃO é preço vira None

@pytest.mark.parametrize('nao_e_preco', [
    None, '', '   ', 'grátis', 'sob consulta', 'R$', '--',
    '0', '0,00', 'R$ 0,00',        # zero é "sem preço", não "de graça"
    '-5', 'R$ -5,00',              # negativo não pode virar positivo calado
    '99999999',                    # não cabe em Numeric(8,2)
    '1,234.56',                    # notação americana: não se adivinha
    '18,50,00',                    # duas vírgulas não formam número
    True, False,                   # bool é int em Python; preço não é sim/não
])
def test_o_que_nao_e_preco_nao_vira_preco(nao_e_preco):
    assert ler_moeda(nao_e_preco) is None, repr(nao_e_preco)


def test_zero_nunca_vira_r_zero_na_tela():
    """O contrato entre o parser e o template: quem devolve None é escondido.

    `formatar_moeda(None)` devolve 'R$ 0,00' de propósito (o painel interno quer
    ver zero numa coluna de total). Por isso o template checa antes de formatar
    — este teste documenta a armadilha para quem mexer nisso depois.
    """
    assert ler_moeda('0') is None
    assert formatar_moeda(None) == 'R$ 0,00'   # o filtro NÃO some sozinho


# ------------------------------------------------- ida e volta com a tela

@pytest.mark.parametrize('digitado,na_tela', [
    ('18,50', 'R$ 18,50'),
    ('18.50', 'R$ 18,50'),
    ('R$ 18,50', 'R$ 18,50'),
    ('18', 'R$ 18,00'),
    ('1.234,56', 'R$ 1.234,56'),
])
def test_o_que_foi_digitado_volta_formatado_em_br(digitado, na_tela):
    assert formatar_moeda(ler_moeda(digitado)) == na_tela


# --------------------------------------------------- e com o dado estruturado

@pytest.mark.parametrize('digitado', ['18,50', '18.50', 'R$ 18,50'])
def test_as_tres_grafias_viram_o_mesmo_preco_no_schema(digitado):
    """Ponto decimal no grafo, vírgula na tela — a partir do mesmo valor."""
    assert _preco_schema(digitado) == '18.50'
    assert formatar_moeda(ler_moeda(digitado)) == 'R$ 18,50'


def test_schema_recusa_o_que_nao_e_preco():
    for nada in (None, '', 'grátis', '0', Decimal('0.00'), '-5'):
        assert _preco_schema(nada) is None, repr(nada)


def test_schema_sai_sem_simbolo_e_sem_separador_de_milhar():
    """`price` é número em texto: 'R$' e '.' de milhar ali dentro invalidam a
    oferta pro Rich Results. A moeda viaja em `priceCurrency`."""
    assert _preco_schema('R$ 1.234,56') == '1234.56'
