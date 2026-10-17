"""Coleta de leads no Brevo: comunidade (/novidades) e donos de bar (/cadastro)."""
import json

import pytest

from app.models.modelo_restaurante import Restaurante


@pytest.fixture
def brevo(monkeypatch):
    """Intercepta a ida ao Brevo e guarda (url, corpo) de cada chamada."""
    chamadas = []

    class Resp:
        status = 201

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def falso_urlopen(req, timeout=None):
        chamadas.append((req.full_url, json.loads(req.data)))
        return Resp()

    import app.utils.email as email
    monkeypatch.setattr(email.urllib.request, 'urlopen', falso_urlopen)
    monkeypatch.setenv('BREVO_API_KEY', 'chave-de-teste')
    monkeypatch.setenv('BREVO_LISTA_COMUNIDADE', '7')
    monkeypatch.setenv('BREVO_LISTA_DONOS', '8')
    monkeypatch.delenv('BREVO_TEMPLATE_DOI', raising=False)
    return chamadas


def _inscreve(client, **extra):
    dados = {'nome': 'Ana', 'email': ' Ana@Barao.com ', 'consentimento': 'sim'}
    dados.update(extra)
    return client.post('/novidades', data=dados)


def test_inscricao_vai_para_lista_da_comunidade(client, session, brevo):
    resp = _inscreve(client, telefone='19 99999-0000')
    assert resp.status_code == 200 and resp.get_json()['ok']
    url, corpo = brevo[-1]
    assert url.endswith('/v3/contacts')
    assert corpo['email'] == 'ana@barao.com' and corpo['listIds'] == [7]
    assert corpo['attributes']['ORIGEM'] == 'home'
    assert corpo['attributes']['TELEFONE'] == '19 99999-0000'
    assert 'CONSENTIMENTO' in corpo['attributes']


def test_com_template_usa_dupla_confirmacao(client, session, brevo, monkeypatch):
    monkeypatch.setenv('BREVO_TEMPLATE_DOI', '3')
    resp = _inscreve(client)
    assert 'confirmar' in resp.get_json()['msg']
    url, corpo = brevo[-1]
    assert url.endswith('/doubleOptinConfirmation')
    assert corpo['includeListIds'] == [7] and corpo['templateId'] == 3
    assert corpo['redirectionUrl'].startswith('http')


def test_origem_do_bar_so_com_slug_existente(client, session, brevo):
    session.add(Restaurante(nome='Bar Lead', slug='bar-lead'))
    session.commit()
    _inscreve(client, bar='bar-lead')
    assert brevo[-1][1]['attributes']['ORIGEM'] == 'bar:bar-lead'
    assert brevo[-1][1]['attributes']['BAR'] == 'Bar Lead'
    _inscreve(client, bar='inventado')
    assert brevo[-1][1]['attributes']['ORIGEM'] == 'home'


def test_sem_consentimento_recusa(client, session, brevo):
    resp = _inscreve(client, consentimento='')
    assert resp.status_code == 400 and brevo == []


def test_email_invalido_recusa(client, session, brevo):
    resp = _inscreve(client, email='sem-arroba')
    assert resp.status_code == 400 and brevo == []


def test_honeypot_finge_sucesso_e_nao_salva(client, session, brevo):
    resp = _inscreve(client, site='http://spam')
    assert resp.get_json()['ok'] and brevo == []


def test_sem_brevo_configurado_nao_quebra(client, session, brevo, monkeypatch):
    monkeypatch.delenv('BREVO_API_KEY')
    resp = _inscreve(client)
    assert resp.status_code == 200 and brevo == []


def test_token_nao_e_cacheado(client):
    resp = client.get('/novidades/token')
    assert resp.headers['Cache-Control'] == 'no-store' and resp.get_json()['token']


def test_home_mostra_formulario_e_segue_cacheavel(client, session):
    resp = client.get('/')
    html = resp.get_data(as_text=True)
    assert 'form-novidades' in html and 'csrf_token' not in html.split('form-novidades')[1][:2000]
    assert 'Cookie' not in resp.headers.get('Vary', '')


def test_cadastro_vira_lead_de_dono(client, session, brevo):
    resp = client.post('/cadastro', data={'nome_bar': 'Bar Novo Lead', 'nome': 'Zé',
                                          'email': 'ze@novo.com', 'senha': 'senha-123'})
    assert resp.status_code == 302
    url, corpo = brevo[-1]
    assert corpo['listIds'] == [8] and corpo['attributes']['ORIGEM'] == 'cadastro'
    assert corpo['attributes']['BAR'] == 'Bar Novo Lead'


def test_cadastro_funciona_com_brevo_fora(client, session, monkeypatch):
    monkeypatch.delenv('BREVO_API_KEY', raising=False)
    resp = client.post('/cadastro', data={'nome_bar': 'Bar Sem Brevo', 'nome': 'Zé',
                                          'email': 'ze@sembrevo.com', 'senha': 'senha-123'})
    assert resp.status_code == 302


@pytest.mark.parametrize('modelo', ['tradicional', 'noturno', 'craft', 'brasa', 'autoral'])
def test_pagina_do_bar_tem_formulario_com_o_slug(client, session, modelo):
    session.add(Restaurante(nome='Bar Form', slug='bar-form'))
    session.commit()
    html = client.get(f'/bar/bar-form?modelo={modelo}').get_data(as_text=True)
    assert 'form-novidades' in html and 'name="bar" value="bar-form"' in html
