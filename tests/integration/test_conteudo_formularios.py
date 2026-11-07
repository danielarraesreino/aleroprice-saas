"""Formulários de conteúdo do painel: erro não apaga o que foi digitado, preço
ilegível avisa, prazo vazio é None, galeria e prato sobem arquivo."""
import io
import re
from decimal import Decimal

import pytest

from app.models.modelo_sitecontent import DishCard, GalleryItem, ProdutoSite
from tests.integration.test_upload_foto_produto import (  # noqa: F401
    _expositor, _png, blob_falso, dona, logado)

MP = 'multipart/form-data'


def test_foto_recusada_devolve_o_que_foi_digitado(logado, dona, blob_falso):
    resp = logado.post('/conteudo/produtos/novo', data={
        'nome': 'Geleia de jabuticaba', 'descricao': 'Feita em tacho', 'preco': '18,50',
        'imagem_arquivo': (io.BytesIO(b'%PDF-1.4'), 'catalogo.pdf'),
    }, content_type=MP)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert 'value="Geleia de jabuticaba"' in html
    assert 'Feita em tacho' in html
    assert 'value="18,50"' in html


def test_heic_explica_o_que_fazer(logado, blob_falso):
    resp = logado.post('/conteudo/produtos/novo', data={
        'nome': 'Geleia', 'imagem_arquivo': (io.BytesIO(b'x'), 'IMG_1.HEIC'),
    }, content_type=MP)
    html = resp.get_data(as_text=True)
    assert 'Manda a foto como JPG ou PNG' in html
    assert 'Mais compatível' in html
    assert 'formato não aceito' not in html


def test_obrigatorio_faltando_mantem_os_outros_campos(logado, dona):
    resp = logado.post('/conteudo/avaliacoes/novo', data={
        'autor': '', 'texto': 'Muito bom', 'estrelas': '4',
    })
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert 'Autor é obrigatório' in html
    assert 'Muito bom' in html
    assert 'value="4"' in html


def test_preco_ilegivel_avisa_e_mantem_o_anterior(logado, dona, session):
    p = ProdutoSite(restaurant_id=dona.restaurant_id, nome='Doce', ativo=True,
                    preco=Decimal('12.00'))
    session.add(p)
    session.commit()
    resp = logado.post(f'/conteudo/produtos/{p.id}/editar', data={
        'nome': 'Doce', 'preco': 'doze reais'}, content_type=MP, follow_redirects=True)
    assert 'Não entendi o preço' in resp.get_data(as_text=True)
    session.refresh(p)
    assert p.preco == Decimal('12.00')


def test_preco_vazio_continua_limpando(logado, dona, session):
    p = ProdutoSite(restaurant_id=dona.restaurant_id, nome='Doce', ativo=True,
                    preco=Decimal('12.00'))
    session.add(p)
    session.commit()
    logado.post(f'/conteudo/produtos/{p.id}/editar', data={'nome': 'Doce', 'preco': ''},
                content_type=MP)
    session.refresh(p)
    assert p.preco is None


def test_prazo_vazio_vira_none(logado, dona, session):
    p = ProdutoSite(restaurant_id=dona.restaurant_id, nome='Doce', ativo=True, prazo_dias=3)
    session.add(p)
    session.commit()
    logado.post(f'/conteudo/produtos/{p.id}/editar', data={'nome': 'Doce', 'prazo_dias': ''},
                content_type=MP)
    session.refresh(p)
    assert p.prazo_dias is None


def test_galeria_sobe_arquivo(logado, dona, blob_falso):
    html = logado.get('/conteudo/galeria/novo').get_data(as_text=True)
    assert 'name="imagem_arquivo"' in html
    assert 'caminho em static' not in html
    resp = logado.post('/conteudo/galeria/novo', data={
        'legenda': 'Barraca', 'imagem_arquivo': (io.BytesIO(_png()), 'barraca.png'),
    }, content_type=MP)
    assert resp.status_code == 302
    g = GalleryItem.query.filter_by(restaurant_id=dona.restaurant_id).one()
    assert re.match(r'https://blob\.test/geleias-da-ana/barraca\.', g.imagem)


def test_galeria_sem_foto_nem_endereco_recusa_e_guarda_legenda(logado, dona):
    resp = logado.post('/conteudo/galeria/novo', data={'legenda': 'Sem foto'}, content_type=MP)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert 'Foto é obrigatório' in html
    assert 'value="Sem foto"' in html
    assert GalleryItem.query.filter_by(restaurant_id=dona.restaurant_id).count() == 0


def test_prato_sobe_arquivo(session, client, blob_falso):
    r = _expositor(session, 'bar-do-ze')
    r.restaurante.tipo_negocio = 'bar'
    session.commit()
    with client.session_transaction() as s:
        s['_user_id'] = str(r.id)
    resp = client.post('/conteudo/cardapio/novo', data={
        'nome': 'Porção', 'imagem_arquivo': (io.BytesIO(_png()), 'porcao.png'),
    }, content_type=MP)
    assert resp.status_code == 302
    d = DishCard.query.filter_by(restaurant_id=r.restaurant_id).one()
    assert d.imagem.startswith('https://blob.test/bar-do-ze/porcao.')


def test_lista_tem_botoes_com_texto_e_44px(logado, dona, session):
    session.add(ProdutoSite(restaurant_id=dona.restaurant_id, nome='Doce', ativo=True))
    session.commit()
    html = logado.get('/conteudo/produtos').get_data(as_text=True)
    for texto in ('Editar', 'Desativar', 'Excluir'):
        assert texto in html
    assert html.count('min-height:44px') >= 3


def test_dashboard_nao_expoe_traceback(app, logado, monkeypatch):
    from app.routes.dashboard import views
    app.config['GESTAO_ATIVA'] = True

    def quebra(*a, **k):
        raise RuntimeError('segredo-interno')
    monkeypatch.setattr(views, 'render_template', quebra)
    resp = logado.get('/app/')
    corpo = resp.get_data(as_text=True)
    assert resp.status_code == 500
    assert 'Traceback' not in corpo and 'segredo-interno' not in corpo
