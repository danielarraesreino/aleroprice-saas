"""O domínio do cliente é dele: ali mora o site do bar e nada mais.

Antes desta separação, `bardavila.bar` respondia `/cadastro` e `/auth/login` —
o site do Gustavo servia o formulário de cadastro dos concorrentes dele e
expunha a administração do produto num endereço que não é nosso.

Estes testes são o que impede isso de voltar: rota de sistema nova nasce
redirecionando, porque a allowlist `ENDPOINTS_DO_TENANT` é fechada.
"""
import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig

PRODUTO = 'feiradebarao.com.br'
CLIENTE = 'bardavila.bar'


@pytest.fixture(autouse=True)
def dominio_do_produto(monkeypatch):
    monkeypatch.setenv('DOMINIO_PRODUTO', PRODUTO)
    # A separação é opt-in: sem o DNS apontando pro produto, redirecionar o
    # login deixaria o operador sem conseguir entrar em lugar nenhum.
    monkeypatch.setenv('SEPARAR_DOMINIOS', '1')


@pytest.fixture
def bar(session):
    r = Restaurante(nome='Bar da Vila', slug='bar-da-vila', dominio=CLIENTE)
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar da Vila'))
    session.commit()
    return r


# ------------------------------------------------ o que FICA no domínio do bar

@pytest.mark.parametrize('rota', ['/', '/bar/bar-da-vila', '/robots.txt'])
def test_site_do_bar_responde_no_dominio_dele(client, bar, rota):
    resp = client.get(rota, headers={'Host': CLIENTE})
    assert resp.status_code == 200


def test_cardapio_abre_no_dominio_do_bar(client, bar, session):
    """O QR colado na mesa aponta pro domínio do bar e tem que abrir ali.

    Sem `public.cardapio` na allowlist, o cliente sentado apontava a câmera e
    via a barra do navegador trocar de bardavila.bar pra feiradebarao.com.br —
    e o `Menu.url` do JSON-LD, que publica o endereço do bar, virava um
    redirecionamento pra outro host.
    """
    from app.models.modelo_sitecontent import DishCard
    # A página só existe com prato ativo (ver `_render_cardapio`); sem isto o
    # 404 mascararia o 302 que este teste procura.
    session.add(DishCard(restaurant_id=bar.id, nome='Costelinha', ativo=True))
    session.commit()

    resp = client.get('/bar/bar-da-vila/cardapio', headers={'Host': CLIENTE})

    assert resp.status_code == 200, (
        f'cardápio saiu do domínio do bar (foi pra {resp.headers.get("Location")})')


def test_reserva_funciona_no_dominio_do_bar(client, bar):
    """O formulário de reserva está na própria página — mandá-lo para outro
    domínio quebraria o fetch e o cliente do bar ficaria sem resposta."""
    resp = client.post('/reservar', headers={'Host': CLIENTE}, data={})

    assert resp.status_code != 302, 'reserva não pode sair do domínio do bar'


# --------------------------------------------- o que SAI do domínio do bar

@pytest.mark.parametrize('rota', [
    '/auth/login', '/cadastro', '/campo/', '/app/', '/config-site/',
    '/conteudo/', '/agenda/', '/promocoes/', '/reservas/', '/campanha/',
])
def test_sistema_nao_responde_no_dominio_do_cliente(client, bar, rota):
    resp = client.get(rota, headers={'Host': CLIENTE})

    assert resp.status_code == 302, f'{rota} não deveria responder no domínio do bar'
    assert resp.headers['Location'] == f'https://{PRODUTO}{rota}', (
        'o redirect precisa preservar o caminho — favorito antigo tem que cair '
        'no lugar certo'
    )


def test_redirect_preserva_querystring(client, bar):
    resp = client.get('/auth/login?next=/app/', headers={'Host': CLIENTE})

    assert resp.headers['Location'] == f'https://{PRODUTO}/auth/login?next=/app/'


# --------------------------------------------- o domínio do produto serve tudo

@pytest.mark.parametrize('rota', ['/', '/barao', '/auth/login', '/cadastro'])
def test_produto_serve_o_sistema(client, rota):
    resp = client.get(rota, headers={'Host': PRODUTO})
    assert resp.status_code == 200


def test_localhost_e_preview_seguem_servindo_tudo(client, bar):
    """Dev e preview da Vercel não podem cair na regra — é onde se trabalha."""
    for host in ('localhost:5000', 'aleroprice-bardavila-abc123.vercel.app'):
        resp = client.get('/auth/login', headers={'Host': host})
        assert resp.status_code == 200, f'{host} deveria servir o sistema'


# --------------------------------------------- o link no site aponta pra fora

def test_link_do_painel_sai_do_dominio_do_bar(client, bar):
    """"Entrar no sistema" dentro do site do bar tem que levar ao produto —
    apontar para /auth/login relativo cairia no próprio redirect."""
    corpo = client.get('/bar/bar-da-vila', headers={'Host': CLIENTE}).get_data(as_text=True)

    assert f'https://{PRODUTO}/auth/login' in corpo
    assert 'href="/auth/login"' not in corpo


def test_sem_o_interruptor_nada_e_redirecionado(client, bar, monkeypatch):
    """Enquanto o DNS do produto não apontar pra cá, o sistema tem que continuar
    respondendo no domínio antigo — senão o operador não loga em lugar nenhum."""
    monkeypatch.delenv('SEPARAR_DOMINIOS', raising=False)

    resp = client.get('/auth/login', headers={'Host': CLIENTE})

    assert resp.status_code == 200
