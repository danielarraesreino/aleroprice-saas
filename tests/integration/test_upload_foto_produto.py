"""O expositor sobe a foto do produto sozinho, pelo painel.

Antes, o campo era um texto pedindo "caminho em static ou URL": quem subia foto
de produto era a organização, pelo Modo Campo. Agora é o mesmo `blob.enviar`
da capa do site, pelo formulário do produto.
"""
import io
import re

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import ProdutoSite
from app.models.usuario import Usuario


def _png():
    from PIL import Image
    saida = io.BytesIO()
    Image.new('RGB', (40, 30), (120, 40, 90)).save(saida, 'PNG')
    return saida.getvalue()


def _expositor(session, slug):
    r = Restaurante(nome=slug, slug=slug, subscription_tier='site',
                    subscription_status='active')
    r.tipo_negocio = 'artesao'
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome=slug))
    u = Usuario(nome='Dona', email=f'dona@{slug}.com', senha='senha-bem-longa',
                tipo='admin', restaurant_id=r.id)
    session.add(u)
    session.commit()
    return u


@pytest.fixture
def dona(session):
    return _expositor(session, 'geleias-da-ana')


@pytest.fixture
def logado(client, dona):
    with client.session_transaction() as s:
        s['_user_id'] = str(dona.id)
    return client


@pytest.fixture
def blob_falso(monkeypatch):
    from app.utils import blob
    monkeypatch.setattr(blob, 'token', lambda: 'tok')
    monkeypatch.setattr(blob, '_para_blob',
                        lambda dados, caminho, ct: f'https://blob.test/{caminho}')


def test_formulario_tem_seletor_de_arquivo(logado):
    html = logado.get('/conteudo/produtos/novo').get_data(as_text=True)
    assert 'enctype="multipart/form-data"' in html
    assert 'name="imagem_arquivo"' in html
    assert 'caminho em static' not in html


def test_upload_grava_a_foto_do_produto(logado, dona, blob_falso):
    resp = logado.post('/conteudo/produtos/novo', data={
        'nome': 'Geleia de jabuticaba',
        'imagem_arquivo': (io.BytesIO(_png()), 'geleia.png'),
    }, content_type='multipart/form-data')

    assert resp.status_code == 302, resp.get_data(as_text=True)
    p = ProdutoSite.query.filter_by(restaurant_id=dona.restaurant_id).one()
    # PNG de foto vira JPEG; o sufixo é o que liga a foto à miniatura.
    assert re.fullmatch(r'https://blob\.test/geleias-da-ana/geleia\.[0-9a-f]{8}\.jpg', p.imagem)


def test_sem_arquivo_mantem_url_ja_gravada(logado, dona, session):
    p = ProdutoSite(restaurant_id=dona.restaurant_id, nome='Doce', ativo=True,
                    imagem='https://exemplo.com/doce.jpg')
    session.add(p)
    session.commit()

    logado.post(f'/conteudo/produtos/{p.id}/editar', data={
        'nome': 'Doce de leite', 'imagem': 'https://exemplo.com/doce.jpg',
    }, content_type='multipart/form-data')

    session.refresh(p)
    assert p.nome == 'Doce de leite'
    assert p.imagem == 'https://exemplo.com/doce.jpg'


def test_tipo_invalido_recusa_e_nao_cria_produto(logado, dona, blob_falso):
    resp = logado.post('/conteudo/produtos/novo', data={
        'nome': 'Geleia',
        'imagem_arquivo': (io.BytesIO(b'%PDF-1.4'), 'catalogo.pdf'),
    }, content_type='multipart/form-data')

    assert resp.status_code == 400
    assert 'formato não aceito' in resp.get_data(as_text=True)
    assert ProdutoSite.query.filter_by(restaurant_id=dona.restaurant_id).count() == 0


def test_outro_expositor_nao_troca_a_foto(logado, session, blob_falso):
    alheia = _expositor(session, 'mel-do-joao')
    p = ProdutoSite(restaurant_id=alheia.restaurant_id, nome='Mel', ativo=True,
                    imagem='https://exemplo.com/mel.jpg')
    session.add(p)
    session.commit()

    resp = logado.post(f'/conteudo/produtos/{p.id}/editar', data={
        'nome': 'Mel', 'imagem_arquivo': (io.BytesIO(_png()), 'troca.png'),
    }, content_type='multipart/form-data')

    assert resp.status_code == 404
    session.refresh(p)
    assert p.imagem == 'https://exemplo.com/mel.jpg'


def test_vitrine_usa_a_miniatura_so_quando_ela_existe(app):
    """URL que `blob.enviar` nomeou tem miniatura ao lado; URL antiga não tem,
    e apontar pra miniatura inexistente quebraria a foto do card."""
    from app.utils.feira import _miniatura

    with app.test_request_context():
        assert (_miniatura('https://x.blob.vercel-storage.com/a/geleia.ab12cd34.jpg')
                == 'https://x.blob.vercel-storage.com/a/geleia.ab12cd34-md.webp')
        antiga = 'https://x.blob.vercel-storage.com/a/geleia-9zKq2Lw0aXb.jpg'
        assert _miniatura(antiga) == antiga
        assert _miniatura('img/nao-existe/foto.jpg').endswith('/img/nao-existe/foto.jpg')
        assert _miniatura(None) is None
