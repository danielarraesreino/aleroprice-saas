"""Logo do expositor: texto solto não pode virar imagem quebrada no topo.

Caso real (2/11): o Viaverde ficou com `logo = 'logo'` no banco. O site montou
`/static/logo` (404) e mostrou imagem quebrada no lugar do monograma.
"""
import io

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.usuario import Usuario
from app.utils.logo import logo_utilizavel


def _png():
    from PIL import Image
    saida = io.BytesIO()
    Image.new('RGB', (40, 30), (120, 40, 90)).save(saida, 'PNG')
    return saida.getvalue()


def test_logo_utilizavel(app):
    with app.app_context():
        assert logo_utilizavel('logo') is None
        assert logo_utilizavel('') is None and logo_utilizavel(None) is None
        assert logo_utilizavel('img/nao/existe.jpg') is None
        assert logo_utilizavel('../app/__init__.py') is None          # não sai de static/
        assert logo_utilizavel('https://blob.test/a/logo.png') == 'https://blob.test/a/logo.png'
        assert logo_utilizavel('favicon.ico') == 'favicon.ico'


def _expositor(session, slug, logo):
    r = Restaurante(nome='Viaverde', slug=slug, subscription_tier='site',
                    subscription_status='active', tipo_negocio='artesao')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Viaverde', logo=logo,
                           whatsapp='5519992359917', horario='Sáb 10h às 16h'))
    session.add(Usuario(nome='Dona', email=f'dona@{slug}.com', senha='senha-bem-longa',
                        tipo='admin', restaurant_id=r.id))
    session.commit()
    return r


def test_logo_solto_vira_monograma(client, session):
    _expositor(session, 'viaverde-teste', 'logo')
    html = client.get('/expositor/viaverde-teste').get_data(as_text=True)
    assert '/static/logo"' not in html
    assert 'class="marca-mono"' in html


def test_logo_que_abre_continua(client, session):
    _expositor(session, 'viaverde-ok', 'https://blob.test/viaverde/logo.png')
    html = client.get('/expositor/viaverde-ok').get_data(as_text=True)
    assert 'https://blob.test/viaverde/logo.png' in html
    assert 'class="marca-mono"' not in html


@pytest.fixture
def logada(client, session):
    r = _expositor(session, 'viaverde-painel', 'logo')
    with client.session_transaction() as s:
        s['_user_id'] = str(Usuario.query.filter_by(restaurant_id=r.id).one().id)
    return r


def test_painel_tem_envio_de_logo_e_limpa_valor_que_nao_abre(client, session, logada):
    html = client.get('/config-site/').get_data(as_text=True)
    assert 'id="logo-arquivo"' in html and 'Logo da marca' in html
    client.post('/config-site/', data={'nome': 'Viaverde', 'logo': 'logo'})
    assert SiteConfig.query.filter_by(restaurant_id=logada.id).one().logo is None


def test_envio_do_logo_grava_so_o_logo(client, session, logada, monkeypatch):
    from app.utils import blob
    monkeypatch.setattr(blob, 'token', lambda: 'tok')
    monkeypatch.setattr(blob, '_para_blob',
                        lambda dados, caminho, ct: f'https://blob.test/{caminho}')
    resp = client.post('/config-site/foto?campo=logo',
                       data={'imagem': (io.BytesIO(_png()), 'logo.png')},
                       content_type='multipart/form-data')
    assert resp.status_code == 200
    cfg = SiteConfig.query.filter_by(restaurant_id=logada.id).one()
    assert cfg.logo.startswith('https://blob.test/') and cfg.hero_foto is None


def test_whatsapp_do_painel_vira_so_digitos(client, session, logada):
    for digitado, guardado in (('(19) 99235-9917', '5519992359917'),
                               ('+55 19 99235-9917', '5519992359917')):
        client.post('/config-site/', data={'nome': 'Viaverde', 'whatsapp': digitado})
        assert SiteConfig.query.filter_by(restaurant_id=logada.id).one().whatsapp == guardado


def test_whatsapp_incompleto_nao_sobrescreve_o_numero_bom(client, session, logada):
    client.post('/config-site/', data={'nome': 'Viaverde', 'whatsapp': '5519992359917'})
    resp = client.post('/config-site/', data={'nome': 'Viaverde', 'whatsapp': '9923'},
                       follow_redirects=True)
    assert 'precisa de DDD' in resp.get_data(as_text=True)
    assert SiteConfig.query.filter_by(restaurant_id=logada.id).one().whatsapp == '5519992359917'


def test_botoes_de_whatsapp_levam_a_sacola(client, session):
    """Com produto marcado, "Encomendar" do topo e do herói levam a lista (não só o
    "Revisar e enviar"). O JS não roda aqui; protege a lógica contra remoção e
    confere que o diálogo e os botões existem."""
    from app.models.modelo_sitecontent import ProdutoSite
    r = _expositor(session, 'viaverde-sacola', None)
    session.add(ProdutoSite(restaurant_id=r.id, nome='Tábua de cedro', imagem='img/x.jpg', ativo=True))
    session.commit()
    html = client.get('/expositor/viaverde-sacola').get_data(as_text=True)
    assert 'class="btn add"' in html and 'id="pedido"' in html
    assert 'genericos.forEach(function(a){a.href=n?envia.href:a.getAttribute(\'data-orig\')})' in html


def test_feira_enquadra_so_quem_esta_perto_da_praca(client, session):
    from app.models.modelo_sitecontent import ProdutoSite  # noqa: F401
    r = _expositor(session, 'viaverde-mapa', None)
    cfg = SiteConfig.query.filter_by(restaurant_id=r.id).one()
    cfg.lat, cfg.lng = -22.881894, -47.041741      # ~7,7 km da Praça
    session.commit()
    html = client.get('/feira').get_data(as_text=True)
    assert 'RAIO_DA_PRACA' in html and 'fitBounds(enquadrar' in html
