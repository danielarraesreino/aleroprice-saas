"""A vitrine da home só mostra barraca cujo /bar/<slug> abre.

A lista sai dos leads versionados, mas quem decide o que está no ar é o banco.
Quando o prazo das prévias passou, a home seguiu anunciando todas as barracas e
cada link dava 404.
"""
from datetime import date, timedelta

from app.models.modelo_restaurante import Restaurante

SLUG = 'emporio-do-nono'   # lead real de Barão, com nota, capa e endereço


def _demo(session, expira_em):
    r = Restaurante(nome='Empório do Nono', slug=SLUG,
                    tipo_conta='demo', demo_expira_em=expira_em)
    session.add(r)
    session.commit()
    return r


def test_barraca_sem_tenant_no_banco_nao_aparece(client, session):
    assert f'/bar/{SLUG}' not in client.get('/').get_data(as_text=True)


def test_barraca_com_previa_no_ar_aparece_e_abre(client, session):
    _demo(session, date.today() + timedelta(days=30))
    assert f'/bar/{SLUG}' in client.get('/').get_data(as_text=True)
    assert client.get(f'/bar/{SLUG}').status_code == 200


def test_prazo_vencido_nao_tira_do_ar(client, session):
    """Não existe mais vencimento automático: só o botão do Modo Campo tira."""
    _demo(session, date.today() - timedelta(days=1))
    assert f'/bar/{SLUG}' in client.get('/').get_data(as_text=True)
    assert client.get(f'/bar/{SLUG}').status_code == 200


def test_barraca_desligada_sai_da_vitrine(client, session):
    r = _demo(session, None)
    r.ativo = False
    session.commit()
    assert f'/bar/{SLUG}' not in client.get('/').get_data(as_text=True)
    assert client.get(f'/bar/{SLUG}').status_code == 404


def test_vitrine_anonima_vai_para_o_cache_da_borda(client, session):
    resp = client.get('/')
    assert 's-maxage=' in resp.headers.get('Cache-Control', '')
    assert 'Set-Cookie' not in resp.headers      # nada de sessão no cache
    # Com `Vary: Cookie` a Vercel não guarda a resposta (medido: só MISS).
    assert 'Cookie' not in resp.headers.get('Vary', '')


def test_vitrine_com_sessao_nao_vai_para_o_cache(client, session):
    client.set_cookie('session', 'qualquer', domain='localhost')
    resp = client.get('/')
    assert 's-maxage' not in resp.headers.get('Cache-Control', '')


def test_site_do_bar_no_dominio_proprio_vai_para_o_cache_sem_sessao(client, session):
    """O formulário de reserva busca o token na hora de enviar, então a página
    do bar é igual para todo visitante e pode sair da borda — sem cookie de
    sessão e sem token embutido."""
    session.add(Restaurante(nome='Bar Proprio', slug='bar-proprio',
                            dominio='barproprio.com.br'))
    session.commit()
    resp = client.get('/', headers={'Host': 'barproprio.com.br'})
    assert resp.status_code == 200
    assert 's-maxage' in resp.headers.get('Cache-Control', '')
    assert 'Set-Cookie' not in resp.headers
    assert 'Cookie' not in resp.headers.get('Vary', '')


def test_previa_espiada_nao_vai_para_o_cache(client, session):
    session.add(Restaurante(nome='Bar Espiado', slug='bar-espiado'))
    session.commit()
    resp = client.get('/bar/bar-espiado?modelo=noturno')
    assert 's-maxage' not in resp.headers.get('Cache-Control', '')


def test_pagina_para_bares_indexavel_sem_prometer_gestao(client, session):
    html = client.get('/site-para-bar-em-campinas').get_data(as_text=True)
    assert 'noindex' not in html and 'rel="canonical"' in html
    assert '"FAQPage"' in html and 'Campinas' in html
    assert 'Em breve' in html and 'Quero o Pro' not in html
    barao = client.get('/barao').get_data(as_text=True)
    assert 'noindex' in barao and 'Quero o Pro' not in barao


def test_home_mostra_horario_da_feira_e_nao_promete_gestao(client, session):
    html = client.get('/').get_data(as_text=True)
    assert 'Sábado' in html and 'Domingo' in html and '"Event"' in html
    assert 'MAIS ESCOLHIDO' not in html and 'lucro limpo' not in html
    assert '/site-para-bar-em-campinas' in html
