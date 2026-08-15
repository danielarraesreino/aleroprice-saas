"""CSRF: quem manda POST tem que provar que veio de uma página nossa.

O `flask-wtf` estava no requirements e o `TestingConfig` já desligava a
checagem — como se a proteção existisse — mas o `CSRFProtect` nunca tinha sido
ligado no app factory. Na prática, todo POST do painel e o formulário público
de reserva aceitavam request forjado de outro site: bastava um `<form>` numa
página qualquer apontando pro nosso endpoint e um clique do usuário logado.

O que estes testes seguram, em ordem de importância:

1. **A reserva pública continua funcionando.** É o POST mais exposto (anônimo,
   de qualquer visitante) e o que mais interessa proteger. Como sobe por
   `fetch` com `FormData(form)`, o token vai num input hidden dentro do
   `<form>` e também no header `X-CSRFToken` — os dois caminhos são testados.
2. **O upload de foto do Modo Campo continua funcionando.** Ali o `FormData` é
   montado à mão no JS, sem `<form>` nenhum: se o token não for junto, a venda
   presencial trava no primeiro clique da câmera.
3. **O webhook do Stripe segue aceitando POST sem token.** Ele chega de fora,
   sem sessão; a autenticação dele é a assinatura HMAC. Sem a isenção, nenhuma
   assinatura seria ativada ou cancelada.

A suíte inteira roda com `WTF_CSRF_ENABLED=False` (TestingConfig), senão cada
`client.post` do resto dos testes precisaria de token. Aqui a gente liga a
checagem só dentro do `with csrf_ligado(app)`, que é o estado de produção.
"""
import hashlib
import hmac
import io
import json
import re
import time
from contextlib import contextmanager

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.usuario import Usuario
from app.utils.modelos import MODELOS


JPEG = b'\xff\xd8\xff\xe0' + b'conteudo' * 8

# O token aparece de duas formas nas páginas: input hidden (formulários) e
# constante de JS (upload do Modo Campo, que não tem <form>).
TOKEN_NO_FORM = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')
TOKEN_NO_JS = re.compile(r'const CSRF = "([^"]+)"')


@contextmanager
def csrf_ligado(app):
    """Liga a checagem de CSRF — o comportamento real de dev e produção."""
    anterior = app.config.get('WTF_CSRF_ENABLED')
    app.config['WTF_CSRF_ENABLED'] = True
    try:
        yield
    finally:
        app.config['WTF_CSRF_ENABLED'] = anterior


@contextmanager
def templates_renderizados(app):
    """Nomes dos templates que a requisição renderizou, na ordem."""
    from flask import template_rendered

    nomes = []

    def anotar(_sender, template, **_extra):
        nomes.append(template.name)

    # weak=False: o receiver é uma função local e o blinker guarda referência
    # fraca por padrão — sem isto ele é coletado antes do primeiro sinal.
    template_rendered.connect(anotar, app, weak=False)
    try:
        yield nomes
    finally:
        template_rendered.disconnect(anotar, app)


def pagina(client, url, **kwargs):
    resp = client.get(url, **kwargs)
    assert resp.status_code == 200, f'{url} respondeu {resp.status_code}'
    return resp.get_data(as_text=True)


def token_do_html(html, padrao=TOKEN_NO_FORM, onde=''):
    achado = padrao.search(html)
    assert achado, f'{onde or "a página"} não trouxe token de CSRF no HTML'
    return achado.group(1)


def token_da_pagina(client, url, padrao=TOKEN_NO_FORM, **kwargs):
    """Pega o token como o navegador pegaria: lendo a página que o servidor deu."""
    return token_do_html(pagina(client, url, **kwargs), padrao, onde=url)


@pytest.fixture
def dono(session, restaurant):
    """Dono do bar de teste — ainda deslogado, pra exercitar o POST de login."""
    usuario = Usuario(nome='Dono', email='dono@bar.test', senha='SenhaTeste123',
                      tipo='admin', restaurant_id=restaurant.id)
    session.add(usuario)
    session.commit()
    return usuario


@pytest.fixture
def bar_publico(session):
    """Bar pagante com site no ar — o dono do formulário de reserva."""
    rest = Restaurante(nome='Bar da Esquina', slug='bar-da-esquina',
                       dominio='baresquina.bar', subscription_tier='site')
    session.add(rest)
    session.commit()
    session.add(SiteConfig(restaurant_id=rest.id, nome='Bar da Esquina',
                           whatsapp='5519999990000'))
    session.commit()
    return rest


def reserva_valida(slug):
    return {'nome': 'Fulano de Tal', 'telefone': '19999999999',
            'data': '2030-01-01', 'hora': '20:00', 'num_pessoas': '2',
            'slug': slug}


# --------------------------------------------------------------- fiação

def test_protecao_esta_ligada_no_app(app):
    """O sintoma original: flask-wtf instalado, config preparado, extensão nunca
    inicializada. `app.extensions['csrf']` é o que prova que ligou."""
    assert 'csrf' in app.extensions


def test_testing_desliga_a_checagem_para_o_resto_da_suite(app):
    """Confirma o que o TestingConfig promete — é o que mantém os outros testes
    passando sem token em cada POST."""
    assert app.config['WTF_CSRF_ENABLED'] is False


def test_guard_de_login_roda_antes_da_checagem_de_csrf(app):
    """A ordem dos `before_request` é comportamento, não detalhe.

    O token morre junto com a sessão. Se o CSRF entrasse na fila antes do
    `require_login`, quem voltasse ao formulário com a sessão expirada levaria
    400 e perderia o que digitou; com esta ordem, cai no login e volta. Mudar o
    lugar do `csrf.init_app` em `create_app` inverte isso em silêncio."""
    ordem = [f.__name__ for f in app.before_request_funcs[None]]

    assert ordem.index('require_login') < ordem.index('csrf_protect'), ordem


def test_todo_formulario_post_carrega_token():
    """Varredura estática de `app/templates/`.

    Um `<form method="post">` sem token não quebra no code review nem no
    happy path do dev (que testa com a suíte, onde o CSRF está desligado): ele
    quebra na cara do usuário, em produção, com 400 e sem explicação. Este
    teste é a rede pra formulário novo — e a lista sobe sozinha quando alguém
    adiciona um.

    Fora do alcance daqui, de propósito: os formulários de reserva do site, que
    não têm `method` (o POST sai por `fetch`) e são cobertos pelo teste dos 6
    modelos, e o upload do Modo Campo, que não tem `<form>`.
    """
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2] / 'app' / 'templates'
    abertura = re.compile(r'<form\b[^>]*>', re.IGNORECASE | re.DOTALL)
    metodo_post = re.compile(r'''method\s*=\s*["']?post["']?''', re.IGNORECASE)

    sem_token = []
    vistos = 0
    for arquivo in sorted(raiz.rglob('*.html')):
        html = arquivo.read_text(encoding='utf-8')
        for tag in abertura.finditer(html):
            if not metodo_post.search(tag.group(0)):
                continue
            vistos += 1
            fim = html.find('</form>', tag.end())
            corpo = html[tag.end():fim if fim != -1 else len(html)]
            if 'csrf_token' not in corpo:
                linha = html.count('\n', 0, tag.start()) + 1
                sem_token.append(f'{arquivo.relative_to(raiz)}:{linha}')

    assert vistos >= 48, f'a varredura achou só {vistos} formulários POST'
    assert not sem_token, 'formulário POST sem csrf_token:\n  ' + '\n  '.join(sem_token)


# --------------------------------------------------------------- login

def test_login_sem_token_e_recusado(app, client, dono):
    with csrf_ligado(app):
        resp = client.post('/auth/login',
                           data={'email': 'dono@bar.test', 'senha': 'SenhaTeste123'})

    assert resp.status_code == 400


def test_login_com_token_da_pagina_passa(app, client, dono):
    with csrf_ligado(app):
        token = token_da_pagina(client, '/auth/login')
        resp = client.post('/auth/login', data={
            'email': 'dono@bar.test', 'senha': 'SenhaTeste123', 'csrf_token': token,
        }, follow_redirects=False)

    assert resp.status_code == 302
    assert '/auth/login' not in resp.headers['Location']


# --------------------------------------------------------------- painel

def test_post_do_painel_sem_token_e_recusado(app, auth_client):
    """Sessão válida não basta: é exatamente esse o request que outro site
    conseguia disparar com o cookie do usuário logado."""
    with csrf_ligado(app):
        resp = auth_client.post('/cardapios/criar', data={
            'nome': 'Cardápio Forjado', 'data_inicio': '2030-01-01',
        })

    assert resp.status_code == 400


def test_post_do_painel_com_token_passa(app, auth_client):
    with csrf_ligado(app):
        token = token_da_pagina(auth_client, '/cardapios/criar')
        resp = auth_client.post('/cardapios/criar', data={
            'nome': 'Cardápio de Verão', 'data_inicio': '2030-01-01',
            'csrf_token': token,
        }, follow_redirects=False)

    assert resp.status_code == 302

    from app.models.modelo_cardapio import Cardapio
    assert Cardapio.query.filter_by(nome='Cardápio de Verão').first() is not None


def test_token_de_outra_sessao_nao_vale(app, auth_client):
    """O token não é uma senha compartilhada: ele é assinado contra a sessão que
    o pediu. É isso que impede o atacante de buscar um token bem-formado numa
    página nossa e embutir no formulário forjado dele."""
    from flask_wtf.csrf import generate_csrf

    with app.test_request_context():
        alheio = generate_csrf()   # token de uma sessão que este cliente nunca teve

    with csrf_ligado(app):
        resp = auth_client.post('/cardapios/criar', data={
            'nome': 'Roubado', 'data_inicio': '2030-01-01', 'csrf_token': alheio,
        })

    assert resp.status_code == 400


# --------------------------------------------------------- reserva pública

def test_reserva_sem_token_e_recusada(app, client, bar_publico):
    with csrf_ligado(app):
        resp = client.post('/reservar', data=reserva_valida(bar_publico.slug),
                           headers={'Host': 'baresquina.bar'})

    assert resp.status_code == 400

    from app.models.modelo_reserva import Reserva
    assert Reserva.query.count() == 0


@pytest.mark.parametrize('modelo', list(MODELOS))
def test_reserva_pelo_formulario_do_site_continua_funcionando(app, client, session,
                                                              bar_publico, modelo):
    """Os modelos servem o mesmo formulário por caminhos diferentes de HTML.
    Um token esquecido em qualquer um deles derruba a reserva só naquele
    modelo — daí percorrer `MODELOS` inteiro (modelo novo entra aqui sozinho),
    pegando o token da página renderizada como o navegador faria.

    O `template_rendered` está aqui porque `arquivo_do_modelo` cai no clássico
    **em silêncio** quando o nome não existe. Sem conferir qual template rodou,
    um modelo com `arquivo` errado no dicionário passaria batido: o teste
    estaria medindo `landing.html` seis vezes."""
    cfg = SiteConfig.query.filter_by(restaurant_id=bar_publico.id).first()
    cfg.modelo = modelo
    session.commit()

    url = f'/bar/{bar_publico.slug}'
    with csrf_ligado(app), templates_renderizados(app) as renderizados:
        html = pagina(client, url)
        assert MODELOS[modelo]['arquivo'] in renderizados, \
            f'{modelo} caiu no fallback: renderizou {renderizados}'
        # o JS não roda aqui, então o teste confere as duas amarrações que ele
        # depende: o campo que o FormData(form) recolhe e o header do fetch
        assert 'X-CSRFToken' in html, f'{modelo}: o fetch da reserva perdeu o header'
        token = token_do_html(html, onde=url)

        dados = reserva_valida(bar_publico.slug)
        dados['csrf_token'] = token          # o que o FormData(form) carrega
        resp = client.post('/reservar', data=dados)

    assert resp.status_code == 200, resp.get_data(as_text=True)[:400]
    assert resp.get_json()['ok'] is True


def test_reserva_aceita_o_token_pelo_header(app, client, bar_publico):
    """Os modelos mandam o mesmo token em `X-CSRFToken`. O header é o caminho
    de quem trocar o FormData por JSON depois."""
    with csrf_ligado(app):
        token = token_da_pagina(client, f'/bar/{bar_publico.slug}')
        resp = client.post('/reservar', data=reserva_valida(bar_publico.slug),
                           headers={'X-CSRFToken': token})

    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


# ------------------------------------------------------------- modo campo

@pytest.fixture
def campo_disco(tmp_path, monkeypatch):
    """Sem BLOB_READ_WRITE_TOKEN o upload grava em disco — aqui, no tmp."""
    from app.utils import demos
    monkeypatch.delenv('BLOB_READ_WRITE_TOKEN', raising=False)
    monkeypatch.setattr(demos, 'DIR_FOTOS', str(tmp_path))
    return tmp_path


@pytest.fixture
def campo(session, client, campo_disco):
    """Operador logado (primeiro tenant) + a prévia de um bar que ele visita."""
    operador = Restaurante(nome='Alero (operador)', slug='alero')
    session.add(operador)
    session.commit()
    session.add(Usuario(nome='Vendedor', email='vendedor@alero.test',
                        senha='segredo123', tipo='admin',
                        restaurant_id=operador.id))
    demo = Restaurante(nome='Boteco da Prévia', slug='boteco-da-previa',
                       tipo_conta='demo')
    session.add(demo)
    session.commit()
    session.add(SiteConfig(restaurant_id=demo.id, nome='Boteco da Prévia'))
    session.commit()

    resp = client.post('/auth/login', data={'email': 'vendedor@alero.test',
                                            'senha': 'segredo123'})
    assert resp.status_code == 302, 'login do operador falhou'
    return demo


def test_upload_de_foto_sem_token_e_recusado(app, client, campo):
    with csrf_ligado(app):
        resp = client.post(f'/campo/{campo.slug}/foto', data={
            'alvo': 'capa', 'imagem': (io.BytesIO(JPEG), 'capa.jpg'),
        }, content_type='multipart/form-data')

    assert resp.status_code == 400


def test_upload_de_foto_com_o_token_da_pagina_continua_funcionando(app, client, campo):
    """O coração da venda presencial. O token sai da constante `CSRF` do JS,
    que é o que o `subir()` põe no FormData montado à mão."""
    with csrf_ligado(app):
        html = pagina(client, f'/campo/{campo.slug}')
        # o upload não tem <form>: o FormData é montado no JS, então o teste
        # confere que o JS entregue realmente põe o token lá dentro
        assert "dados.append('csrf_token', CSRF)" in html, \
            'o FormData do upload perdeu o token'
        token = token_do_html(html, TOKEN_NO_JS, onde='campo/editar')

        resp = client.post(f'/campo/{campo.slug}/foto', data={
            'alvo': 'capa', 'imagem': (io.BytesIO(JPEG), 'capa.jpg'),
            'csrf_token': token,
        }, content_type='multipart/form-data')

    assert resp.status_code == 200, resp.get_data(as_text=True)[:400]
    assert resp.get_json()['ok'] is True

    cfg = SiteConfig.query.filter_by(restaurant_id=campo.id).first()
    assert cfg.hero_foto, 'a capa não foi gravada'


def test_formulario_do_modo_campo_leva_token(app, client, campo):
    """O upload é fetch, mas o resto da tela é `<form method=post>` comum."""
    with csrf_ligado(app):
        token = token_da_pagina(client, f'/campo/{campo.slug}')
        resp = client.post(f'/campo/{campo.slug}/basico',
                           data={'nome': 'Boteco Renomeado', 'csrf_token': token},
                           follow_redirects=False)

    assert resp.status_code == 302
    cfg = SiteConfig.query.filter_by(restaurant_id=campo.id).first()
    assert cfg.nome == 'Boteco Renomeado'


# ------------------------------------------------------------ webhook Stripe

def _assinar(payload: bytes, secret: str) -> str:
    """Header Stripe-Signature válido (mesmo esquema de tests/test_billing_security)."""
    timestamp = int(time.time())
    v1 = hmac.new(secret.encode(), f'{timestamp}.{payload.decode()}'.encode(),
                  hashlib.sha256).hexdigest()
    return f't={timestamp},v1={v1}'


def test_webhook_do_stripe_passa_sem_token(app, client, restaurant, monkeypatch):
    """O Stripe não tem sessão nem token. Sem `@csrf.exempt` aqui, todo evento
    de cobrança voltaria 400 e ninguém seria ativado nem rebaixado."""
    segredo = 'whsec_segredo_de_teste'
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', segredo)

    corpo = json.dumps({
        'type': 'checkout.session.completed',
        'data': {'object': {'client_reference_id': str(restaurant.id),
                            'payment_status': 'paid',
                            'metadata': {'plano': 'pro'}}},
    }).encode()

    with csrf_ligado(app):
        resp = client.post('/billing/webhook', data=corpo,
                           content_type='application/json',
                           headers={'Stripe-Signature': _assinar(corpo, segredo)})

    assert resp.status_code == 200, resp.get_data(as_text=True)[:400]
    assert resp.get_json()['success'] is True
    assert restaurant.subscription_tier == 'pro'


def test_webhook_sem_assinatura_valida_continua_recusado(app, client, monkeypatch):
    """A isenção de CSRF não afrouxa o webhook: quem autentica ali é o HMAC."""
    monkeypatch.setenv('STRIPE_WEBHOOK_SECRET', 'whsec_segredo_de_teste')

    with csrf_ligado(app):
        resp = client.post('/billing/webhook', data=b'{}',
                           content_type='application/json',
                           headers={'Stripe-Signature': 't=1,v1=mentira'})

    assert resp.status_code == 400
    # 400 do Stripe (assinatura), não do CSRF — o corpo diz qual dos dois.
    assert resp.get_json()['error'] == 'invalid signature'
