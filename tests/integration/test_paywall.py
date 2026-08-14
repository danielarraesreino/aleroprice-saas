"""Quem paga edita; quem não paga continua no ar, mas congelado.

A tabela `ROTAS_PROTEGIDAS` é de propósito o checklist: rota de escrita que
não estiver nela é rota sem gate. Ao criar endpoint novo no CMS, adicione aqui.

Exceção conhecida: `/campo/*` (Modo Campo) não é gated por plano e sim por
`e_operador()` — é ferramenta de venda do operador, não feature de cliente, e
responde 404 em vez de mandar pra `/upgrade`. Coberto em `test_campo.py`.

Regra que não pode regredir: **o site do bar nunca sai do ar** por falta de
pagamento. Um bar imprime QR e põe o link no Instagram; derrubar isso pune o
cliente do bar, não o bar.
"""
from datetime import date, timedelta

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.usuario import Usuario

# (metodo, url, plano_minimo)
ROTAS_PROTEGIDAS = [
    ('POST', '/config-site/', 'site'),
    ('POST', '/conteudo/cardapio/novo', 'site'),
    ('POST', '/agenda/novo', 'site'),
    ('POST', '/promocoes/nova', 'site'),
    ('GET', '/app/relatorio/pratos', 'pro'),
    ('GET', '/app/relatorio/categorias', 'pro'),
]


def _bar(session, slug, **kwargs):
    r = Restaurante(nome=slug.replace('-', ' ').title(), slug=slug, **kwargs)
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome=r.nome, whatsapp='5519999990000'))
    u = Usuario(nome='Dono', email=f'{slug}@x.com', senha='segredo123',
                tipo='admin', restaurant_id=r.id)
    session.add(u)
    session.commit()
    return r, u


def _login(client, email):
    return client.post('/auth/login', data={'email': email, 'senha': 'segredo123'})


@pytest.mark.parametrize('metodo,url,minimo', ROTAS_PROTEGIDAS)
def test_free_nao_escreve(client, session, metodo, url, minimo):
    """Plano free bate no paywall e é mandado pra tela de upgrade."""
    _bar(session, 'bar-free')
    _login(client, 'bar-free@x.com')

    resp = client.open(url, method=metodo, data={})

    assert resp.status_code == 302, f'{metodo} {url} não tem gate'
    assert '/upgrade' in resp.headers['Location']


@pytest.mark.parametrize('metodo,url,minimo', ROTAS_PROTEGIDAS)
def test_trial_tem_acesso_total(client, session, metodo, url, minimo):
    """Durante o teste grátis a pessoa vê o produto inteiro."""
    _bar(session, 'bar-trial', trial_termina_em=date.today() + timedelta(days=7))
    _login(client, 'bar-trial@x.com')

    resp = client.open(url, method=metodo, data={})

    assert resp.status_code != 302 or '/upgrade' not in resp.headers.get('Location', '')


def test_plano_site_nao_alcanca_gestao(client, session):
    _bar(session, 'bar-site', subscription_tier='site')
    _login(client, 'bar-site@x.com')

    resp = client.get('/app/relatorio/pratos')

    assert resp.status_code == 302
    assert '/upgrade' in resp.headers['Location']


def test_plano_site_edita_o_site(client, session):
    _bar(session, 'bar-site2', subscription_tier='site')
    _login(client, 'bar-site2@x.com')

    assert client.get('/config-site/').status_code == 200
    assert client.get('/agenda/novo').status_code == 200


def test_site_do_bar_free_continua_no_ar(client, session):
    """O ponto inegociável da degradação."""
    _bar(session, 'bar-free2')

    resp = client.get('/bar/bar-free2')

    assert resp.status_code == 200
    assert 'Bar Free2' in resp.get_data(as_text=True)


def test_free_perde_o_formulario_mas_ganha_whatsapp(client, session):
    _bar(session, 'bar-free3')

    corpo = client.get('/bar/bar-free3').get_data(as_text=True)

    assert 'reservaForm' not in corpo
    assert 'Chamar no WhatsApp' in corpo
    assert '5519999990000' in corpo


def test_reserva_por_post_direto_e_recusada(client, session):
    """Esconder o form no HTML não é gate — o servidor precisa recusar."""
    _bar(session, 'bar-free4')

    resp = client.post('/reservar', data={
        'nome': 'Fulano', 'telefone': '19999999999',
        'data': (date.today() + timedelta(days=2)).isoformat(),
        'hora': '20:00', 'num_pessoas': '2', 'slug': 'bar-free4',
    })

    assert resp.status_code == 403
    assert resp.get_json()['ok'] is False


def test_bar_pagante_recebe_reserva(client, session):
    _bar(session, 'bar-pago', subscription_tier='site')

    resp = client.post('/reservar', data={
        'nome': 'Fulano', 'telefone': '19999999999',
        'data': (date.today() + timedelta(days=2)).isoformat(),
        'hora': '20:00', 'num_pessoas': '2', 'slug': 'bar-pago',
    })

    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


def test_limite_de_conteudo_no_free(client, session):
    from app.models.modelo_sitecontent import DishCard
    r, _ = _bar(session, 'bar-limite', trial_termina_em=date.today() + timedelta(days=5))
    for i in range(5):
        session.add(DishCard(restaurant_id=r.id, nome=f'Prato {i}', ordem=i, ativo=True))
    session.commit()

    # ainda em trial: passa do limite do free sem problema
    _login(client, 'bar-limite@x.com')
    resp = client.post('/conteudo/cardapio/novo', data={'nome': 'Prato 6', 'ordem': '6'})
    assert resp.status_code == 302
    assert DishCard.query.filter_by(restaurant_id=r.id).count() == 6

    # trial vence: novo item é barrado
    r.trial_termina_em = date.today() - timedelta(days=1)
    session.commit()
    resp = client.post('/conteudo/cardapio/novo', data={'nome': 'Prato 7', 'ordem': '7'})
    assert DishCard.query.filter_by(restaurant_id=r.id).count() == 6
