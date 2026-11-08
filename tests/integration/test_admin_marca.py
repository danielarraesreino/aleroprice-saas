"""O admin tem a cara da Feira: marca, favicon, CSS próprio e sem restos do Alero."""
import re

RESTOS = ('Alero', 'AleroPrice', 'Lucratividade', 'Erro: Restaurante')


def _visivel(html):
    """Texto que o usuário lê: sem <script>, <style> e comentários."""
    html = re.sub(r'(?s)<(script|style)\b.*?</\1>', '', html)
    return re.sub(r'(?s)<!--.*?-->', '', html)


def test_login_tem_a_marca_e_nao_tem_resto_de_outro_produto(client):
    html = client.get('/auth/login').get_data(as_text=True)
    assert 'css/admin.css' in html and 'css/fontes.css' in html
    assert 'favicon' in html
    assert '<h1>Entrar</h1>' in html and 'E-mail' in html
    assert 'class="navbar-brand"' in html and '<span>Barão</span>' in html
    assert not any(r in _visivel(html) for r in RESTOS)


def test_erro_de_login_tem_acento_e_ponto(client, session):
    resp = client.post('/auth/login', data={'email': 'x@y.com', 'senha': 'errada'},
                       follow_redirects=True)
    assert 'E-mail ou senha inválidos.' in resp.get_data(as_text=True)


def test_telas_do_dono_usam_o_tema_e_sem_restos(auth_client, session, restaurant):
    restaurant.subscription_tier = 'site'
    restaurant.subscription_status = 'active'
    session.commit()
    for rota in ('/config-site/numeros', '/promocoes/', '/conteudo/'):
        html = auth_client.get(rota, follow_redirects=True).get_data(as_text=True)
        assert 'css/admin.css' in html, rota
        assert 'navbar-feira' in html, rota
        assert not any(r in _visivel(html) for r in RESTOS), rota


def test_titulo_da_home_do_painel_nao_e_de_gestao(auth_client):
    html = auth_client.get('/app/index', follow_redirects=True).get_data(as_text=True)
    assert '<title>Seu site' in html
