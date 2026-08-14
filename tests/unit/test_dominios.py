"""Consulta de domínio pelo nome do bar.

O requisito que manda aqui é o **falso positivo**: dizer "está livre" para um
domínio registrado faz o vendedor repetir isso na frente do dono e descobrir o
contrário na hora de registrar. Por isso toda falha de consulta vira `None`
("conferir"), nunca `True`.
"""
import urllib.error

import pytest

from app.utils import dominios


class RespostaFalsa:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def erro_http(codigo):
    def _lanca(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, codigo, 'x', {}, None)
    return _lanca


# ------------------------------------------------------------- candidatos

def test_nome_vira_dominio_sem_hifen_nem_acento():
    """Bar quase nunca registra com hífen — "bardoze.com.br", não "bar-do-ze"."""
    assert dominios.candidatos('Bar do Zé')[0] == 'bardoze.com.br'
    assert dominios.candidatos('Cervejaria Tábuas')[0] == 'cervejariatabuas.com.br'


def test_com_br_vem_antes_de_net_br():
    lista = dominios.candidatos('Boteco X')
    assert lista.index('botecox.com.br') < lista.index('botecox.net.br')


def test_cidade_gera_alternativa_quando_o_nome_e_generico():
    lista = dominios.candidatos('Botequim', cidade='Barão Geraldo')
    assert 'botequim.com.br' in lista
    assert 'botequimbaraogeraldo.com.br' in lista


def test_cidade_composta_usa_so_o_primeiro_termo():
    """`cidade_uf` chega como "Barão Geraldo, Campinas–SP" — o campo inteiro
    geraria "cervejariatabuasbaraogeraldocampinassp.com.br"."""
    lista = dominios.candidatos('Tábuas', cidade='Barão Geraldo, Campinas–SP')
    assert 'tabuasbaraogeraldo.com.br' in lista
    assert not any('campinassp' in d for d in lista)


def test_nome_longo_nao_ganha_variacao_com_cidade():
    """Domínio que não cabe num cartão nem se fala no telefone não vale oferecer."""
    lista = dominios.candidatos('Cervejaria Tábuas', cidade='Barão Geraldo, Campinas–SP')
    assert 'cervejariatabuas.com.br' in lista
    assert all(len(d) <= dominios.LIMITE_ROTULO + 11 for d in lista), lista


def test_prefixo_bar_so_quando_o_nome_nao_comeca_com_bar():
    assert 'barbotequim.com.br' in dominios.candidatos('Botequim')
    assert 'barbardoze.com.br' not in dominios.candidatos('Bar do Zé')


def test_nome_vazio_nao_gera_candidato():
    assert dominios.candidatos('') == []
    assert dominios.candidatos(None) == []


# ------------------------------------------------------------- disponivel

def test_404_no_rdap_significa_livre(monkeypatch):
    monkeypatch.setattr(dominios.urllib.request, 'urlopen', erro_http(404))
    assert dominios.disponivel('tabuascervejaria.com.br') is True


def test_200_no_rdap_significa_registrado(monkeypatch):
    monkeypatch.setattr(dominios.urllib.request, 'urlopen',
                        lambda req, timeout=None: RespostaFalsa(200))
    assert dominios.disponivel('globo.com.br') is False


@pytest.mark.parametrize('falha', [
    urllib.error.URLError('sem rede'),
    TimeoutError('estourou'),
    OSError('conexão fechada'),
])
def test_falha_de_rede_vira_conferir_e_nao_livre(monkeypatch, falha):
    def explode(req, timeout=None):
        raise falha
    monkeypatch.setattr(dominios.urllib.request, 'urlopen', explode)

    assert dominios.disponivel('bardoze.com.br') is None


def test_rate_limit_nao_e_resposta_sobre_o_dominio(monkeypatch):
    """429 fala do nosso uso do RDAP, não do domínio — não pode virar 'livre'."""
    monkeypatch.setattr(dominios.urllib.request, 'urlopen', erro_http(429))
    assert dominios.disponivel('bardoze.com.br') is None


def test_dominio_vazio_nao_consulta():
    assert dominios.disponivel('') is None


# ------------------------------------------------------------- consultar

def test_consultar_respeita_o_limite_de_idas_a_rede(monkeypatch):
    """A proposta carrega com o dono do bar olhando: nada de 6 consultas."""
    chamadas = []

    def contar(req, timeout=None):
        chamadas.append(req.full_url)
        raise urllib.error.HTTPError(req.full_url, 404, 'x', {}, None)

    monkeypatch.setattr(dominios.urllib.request, 'urlopen', contar)
    resultado = dominios.consultar('Botequim de Barão', cidade='Campinas', limite=2)

    assert len(resultado) == 2
    assert len(chamadas) == 2
    assert all(item['livre'] is True for item in resultado)


def test_primeiro_livre_ignora_registrado_e_indefinido():
    consulta = [
        {'dominio': 'a.com.br', 'livre': False},
        {'dominio': 'b.com.br', 'livre': None},
        {'dominio': 'c.com.br', 'livre': True},
    ]
    assert dominios.primeiro_livre(consulta) == 'c.com.br'


def test_sem_nenhum_confirmado_nao_inventa():
    consulta = [{'dominio': 'a.com.br', 'livre': None},
                {'dominio': 'b.com.br', 'livre': False}]
    assert dominios.primeiro_livre(consulta) is None


# ------------------------------------------------------------- taxa

def test_taxa_so_existe_com_env(monkeypatch):
    monkeypatch.delenv('FEIRA_TAXA_SETUP', raising=False)
    assert dominios.taxa_de_instalacao() is None

    monkeypatch.setenv('FEIRA_TAXA_SETUP', '97')
    assert dominios.taxa_de_instalacao() == '97'
