"""A página de upgrade tem que abrir.

Ela respondia 500 por um `NameError`: o módulo não importa `current_user` no
topo e a rota usava mesmo assim. Ninguém percebeu porque nenhum teste a abria —
e é justamente a tela que o cliente do plano Site encontra quando esbarra num
recurso do Pro. O momento em que ele consideraria pagar mais terminava em erro.
"""
import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario
from app.utils.planos import precos


@pytest.fixture
def dono(session):
    r = Restaurante(nome='Bar Upgrade', slug='bar-upgrade')
    r.tipo_conta = 'cliente'
    r.subscription_tier = 'site'
    session.add(r)
    session.commit()
    u = Usuario(nome='Dono', email='dono@barupgrade.com.br',
                senha='senha-bem-longa-123', tipo='admin', restaurant_id=r.id)
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def logado(client, dono):
    with client.session_transaction() as s:
        s['_user_id'] = str(dono.id)
    return client


def test_upgrade_abre(logado):
    assert logado.get('/app/upgrade').status_code == 200


def test_upgrade_mostra_o_preco_que_o_sistema_cobra(logado):
    """Sem isto, a tela de venda interna pode divergir da tabela, como já
    aconteceu entre a landing e a cobrança."""
    html = logado.get('/app/upgrade').get_data(as_text=True)

    assert precos()['site'] in html
    assert precos()['pro'] in html
