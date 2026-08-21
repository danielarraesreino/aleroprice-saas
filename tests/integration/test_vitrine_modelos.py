"""A vitrine dos modelos e o que ela não pode contaminar.

Duas regras aqui valem dinheiro:

1. Bar-vitrine é material de venda, não prospecção. Se entrar no funil, "abertas
   pelo dono" passa a contar as vezes que o VENDEDOR abriu a demonstração — e a
   única métrica da campanha vira ficção.
2. A página é interna. Ela lista bares fictícios e explica o roteiro de venda;
   404 pra quem não é operador, não 403 — painel interno não se anuncia.
"""
import pytest
from markupsafe import escape

from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario
from app.routes.campanha.views import FONTE_VITRINE, VITRINE


@pytest.fixture
def operador(session):
    rest = Restaurante(nome='Alero (operador)', slug='alero')
    session.add(rest)
    session.commit()
    usuario = Usuario(nome='Vendedor', email='vendedor@alero.com',
                      senha='segredo123', tipo='superadmin', restaurant_id=rest.id)
    session.add(usuario)
    session.commit()
    return usuario


@pytest.fixture
def logado(client, operador):
    with client.session_transaction() as s:
        s['_user_id'] = str(operador.id)
    return client


def test_pagina_lista_os_seis_modelos(logado):
    resp = logado.get('/campanha/modelos')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    for modelo, _, bar, _, _ in VITRINE:
        assert modelo in html, f'{modelo} não aparece na vitrine'
        # "Fogo & Sal" sai como "Fogo &amp; Sal": o Jinja escapa, e é o certo.
        assert escape(bar) in html, f'{bar} não aparece na vitrine'


def test_link_de_previa_aparece_quando_o_bar_existe(logado, session):
    """Com o bar aplicado, o cartão vira link com `?modelo=` — que é o que
    mostra a opção sem gravar nada no site de ninguém."""
    modelo, slug, nome, _, _ = VITRINE[1]   # craft / Tap Cinco
    r = Restaurante(nome=nome, slug=slug)
    r.tipo_conta = 'demo'
    session.add(r)
    session.commit()

    html = logado.get('/campanha/modelos').get_data(as_text=True)

    assert f'modelo={modelo}' in html
    assert f'/bar/{slug}' in html


def test_avisa_quando_o_bar_de_demonstracao_nao_foi_aplicado(logado):
    """Cartão com link quebrado na frente do dono do bar é pior que cartão
    apagado: o vendedor toca, abre 404, e perde a conversa."""
    html = logado.get('/campanha/modelos').get_data(as_text=True)
    assert 'falta aplicar' in html
    assert 'flask aplicar-demos' in html


def test_nao_operador_leva_404(client, operador, session):
    """Dono de bar logado não vê o painel interno.

    A fixture `operador` precisa vir junto: `e_operador` é "pertence ao primeiro
    tenant" (`app/utils/operador.py`), então sem um tenant anterior o próprio
    bar do teste seria o primeiro — e passaria por operador.
    """
    r = Restaurante(nome='Bar Qualquer', slug='bar-qualquer')
    session.add(r)
    session.commit()
    assert r.id > operador.restaurant_id, 'o bar do teste tem que vir depois'

    u = Usuario(nome='Dono', email='dono@barqualquer.com.br',
                senha='senha-bem-longa', tipo='admin', restaurant_id=r.id)
    session.add(u)
    session.commit()
    with client.session_transaction() as s:
        s['_user_id'] = str(u.id)

    assert client.get('/campanha/modelos').status_code == 404
    assert client.get('/campanha/').status_code == 404


class TestFunilNaoContaVitrine:
    def _linha(self, session, nome, slug, fonte, visitas):
        r = Restaurante(nome=nome, slug=slug)
        r.tipo_conta = 'demo'
        r.demo_fonte = fonte
        r.demo_visitas = visitas
        session.add(r)
        session.commit()
        return r

    def test_vitrine_fica_fora_da_conta(self, logado, session):
        self._linha(session, 'Bar Real', 'bar-real-1', 'relatorio-rmc', 3)
        self._linha(session, 'Vitrine X', 'vitrine-x', FONTE_VITRINE, 40)

        html = logado.get('/campanha/').get_data(as_text=True)

        # A vitrine aparece na tabela (marcada), mas não infla o funil: com ela
        # dentro, "prévias" seria 2 e "abertas" contaria as 40 visitas do
        # vendedor abrindo a demonstração.
        assert 'Vitrine X' in html
        assert 'demonstração' in html
        import re
        numeros = re.findall(r'display-6 text-\w+">\s*(\d+)', html)
        assert numeros[0] == '1', f'prévias deveria ser 1 (só o bar real), veio {numeros[0]}'
