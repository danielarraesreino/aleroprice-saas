from flask import url_for

def test_home_page(client):
    """A raiz de um Host desconhecido é a landing do produto (venda).

    Antes este teste esperava a marca 'AleroPrice' — a raiz servia o dashboard.
    Hoje `/` é decidida pelo Host: domínio de bar serve o bar, qualquer outro
    serve a landing de venda.
    """
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert b"FEIRA DE" in response.data


def test_home_page_de_um_dominio_de_bar_serve_o_bar(client, restaurant):
    """Host que bate com Restaurante.dominio serve o site daquele bar."""
    from app.extensions import db
    restaurant.dominio = 'bardavila.bar'
    restaurant.slug = 'bar-da-vila'
    db.session.commit()

    response = client.get('/', headers={'Host': 'bardavila.bar'})
    assert response.status_code == 200
    assert b"FEIRA DE" not in response.data
    assert restaurant.nome.encode() in response.data


def test_bar_por_slug_inexistente_404(client):
    assert client.get('/bar/nao-existe').status_code == 404

def test_pratos_index(client):
    """Testa se a lista de pratos carrega"""
    response = client.get('/pratos/', follow_redirects=True)
    assert response.status_code == 200
    # Verifica se o template base está lá (header/footer)
    assert b"<html" in response.data

def test_dashboard_index(client):
    """Testa se o dashboard carrega (montado em '/')."""
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200

def test_seed_vegan_route_gated(client):
    """A rota /seed-vegan é perigosa (dispara seed) e agora fica atrás de
    ENABLE_ADMIN_ENDPOINTS. Sem a flag (padrão, inclusive em produção) ela
    NÃO deve estar registrada — 404 é o comportamento seguro esperado."""
    response = client.get('/seed-vegan', follow_redirects=True)
    assert response.status_code == 404
