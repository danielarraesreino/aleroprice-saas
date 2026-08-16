"""O dono troca a própria foto de capa.

Antes disto, o campo de capa no painel era um texto pedindo "caminho em static,
ex: img/bar/foto-18.jpg". O uploader existia, mas só no Modo Campo — que é
ferramenta do operador e responde 404 pro cliente. Ou seja: a única pessoa que
podia pôr foto no site do bar era quem tinha vendido.
"""
import io

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.usuario import Usuario


def _png():
    """PNG 1x1 de verdade — o uploader valida o conteúdo, não a extensão."""
    return (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00'
            b'\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')


@pytest.fixture
def dono(session):
    r = Restaurante(nome='Bar do Teste', slug='bar-do-teste')
    r.tipo_conta = 'cliente'
    r.subscription_tier = 'site'
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar do Teste'))
    u = Usuario(nome='Dono', email='dono@bardoteste.com.br',
                senha='senha-bem-longa', tipo='admin', restaurant_id=r.id)
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def logado(client, dono):
    with client.session_transaction() as s:
        s['_user_id'] = str(dono.id)
    return client


def test_tela_de_site_tem_botao_de_foto_e_nao_campo_de_caminho(logado):
    """O dono precisa ver 'escolher foto', não um campo pedindo caminho."""
    html = logado.get('/config-site/index').get_data(as_text=True)

    assert 'type="file"' in html, 'não há seletor de arquivo na tela do cliente'
    assert 'Escolher foto' in html
    # O texto antigo dizia "caminho em static, ex: img/bar/foto-18.jpg".
    assert 'caminho em static' not in html


def test_upload_grava_a_capa_no_site(logado, dono, session, monkeypatch):
    """O caminho feliz: sobe a foto e ela vira o hero do site."""
    from app.utils import blob
    monkeypatch.setattr(blob, 'enviar',
                        lambda arquivo, slug: f'https://blob.test/{slug}/capa.jpg')

    resp = logado.post('/config-site/foto', data={
        'imagem': (io.BytesIO(_png()), 'foto.png'),
    }, content_type='multipart/form-data')

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()['ok'] is True

    cfg = SiteConfig.query.filter_by(restaurant_id=dono.restaurant_id).first()
    assert cfg.hero_foto == 'https://blob.test/bar-do-teste/capa.jpg'


def test_upload_indisponivel_diz_o_motivo(logado, monkeypatch):
    """Blob mal configurado é erro de infraestrutura, não do dono.

    503 e a mensagem original — dizer 'erro' e engolir a causa faz o dono
    tentar de novo com outra foto, que não é o problema.
    """
    from app.utils import blob

    def explode(arquivo, slug):
        raise blob.UploadIndisponivel('armazenamento não configurado')
    monkeypatch.setattr(blob, 'enviar', explode)

    resp = logado.post('/config-site/foto', data={
        'imagem': (io.BytesIO(_png()), 'foto.png'),
    }, content_type='multipart/form-data')

    assert resp.status_code == 503
    assert 'armazenamento' in resp.get_json()['erro']


def test_visitante_sem_login_nao_sobe_foto(client):
    resp = client.post('/config-site/foto', data={
        'imagem': (io.BytesIO(_png()), 'foto.png'),
    }, content_type='multipart/form-data')

    assert resp.status_code in (302, 401, 403, 404), \
        'upload aberto pra quem não está logado'
