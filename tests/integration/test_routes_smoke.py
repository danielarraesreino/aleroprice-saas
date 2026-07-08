from flask import url_for

def test_home_page(client):
    """Testa se a página inicial carrega"""
    response = client.get('/', follow_redirects=True)
    assert response.status_code == 200
    assert b"AleroPrice" in response.data

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
