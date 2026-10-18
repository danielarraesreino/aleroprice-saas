"""Esqueci minha senha: link por e-mail (Brevo), 30 min, uso único."""
import re

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario


@pytest.fixture
def enviados(monkeypatch):
    caixa = []
    import app.utils.email as email
    monkeypatch.setattr(email, 'enviar_email',
                        lambda para, assunto, html: caixa.append((para, html)) or True)
    return caixa


@pytest.fixture
def dono(session):
    r = Restaurante(nome='Bar Senha', slug='bar-senha')
    session.add(r)
    session.commit()
    u = Usuario(nome='Dono', email='dono@senha.com', senha='antiga-123',
                tipo='admin', restaurant_id=r.id)
    session.add(u)
    session.commit()
    return u


def _link(caixa):
    return re.search(r'href="https?://[^/]+(/auth/redefinir/[^"]+)"', caixa[-1][1]).group(1)


def test_login_tem_olho_e_link_de_esqueci(client):
    html = client.get('/auth/login').get_data(as_text=True)
    assert 'Mostrar senha' in html and '/auth/esqueci' in html


def test_pede_link_e_troca_a_senha_uma_vez(client, dono, enviados):
    resp = client.post('/auth/esqueci', data={'email': ' Dono@Senha.com '})
    assert resp.status_code == 302 and len(enviados) == 1
    link = _link(enviados)

    assert 'Mostrar senha' in client.get(link).get_data(as_text=True)
    client.post(link, data={'senha': 'nova-senha-123'})
    assert Usuario.query.get(dono.id).verificar_senha('nova-senha-123')

    # uso único: depois da troca o mesmo link não serve mais
    resp = client.get(link)
    assert '/auth/esqueci' in resp.headers['Location']


def test_email_inexistente_tem_a_mesma_resposta_e_nao_envia(client, session, enviados):
    resp = client.post('/auth/esqueci', data={'email': 'ninguem@x.com'}, follow_redirects=True)
    assert 'Se esse e-mail tiver conta' in resp.get_data(as_text=True)
    assert enviados == []


def test_senha_curta_e_recusada(client, dono, enviados):
    client.post('/auth/esqueci', data={'email': 'dono@senha.com'})
    client.post(_link(enviados), data={'senha': '123'})
    assert Usuario.query.get(dono.id).verificar_senha('antiga-123')


def test_token_falso_nao_entra(client, session):
    resp = client.get('/auth/redefinir/token-falso')
    assert '/auth/esqueci' in resp.headers['Location']


def test_login_nao_redireciona_para_outro_site(client, dono):
    for destino in ('//golpe.com/x', '/\\golpe.com', 'https://golpe.com'):
        resp = client.post(f'/auth/login?next={destino}',
                           data={'email': 'dono@senha.com', 'senha': 'antiga-123'})
        assert resp.status_code == 302
        assert 'golpe' not in resp.headers['Location']
        client.get('/auth/logout')


def test_conta_desativada_nao_entra(client, dono, session):
    dono.ativo = False
    session.commit()
    resp = client.post('/auth/login', data={'email': 'dono@senha.com', 'senha': 'antiga-123'},
                       follow_redirects=True)
    assert 'inválidos' in resp.get_data(as_text=True)
