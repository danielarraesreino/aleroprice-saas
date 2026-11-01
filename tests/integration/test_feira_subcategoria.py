"""Páginas por subcategoria (/feira/<cat>/<sub>) e o sitemap que as anuncia.

A subcategoria vem do que o expositor escreveu no campo categoria
(`app/utils/categorias.py`), então "Vasos de cerâmica" e "Cerâmica" caem na
mesma página sem ninguém reclassificar nada.
"""
import xml.etree.ElementTree as ET

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import ProdutoSite

PRODUTO = 'feiradebarao.com.br'


def _artesao(session, slug, *produtos):
    r = Restaurante(nome=slug, slug=slug, tipo_negocio='artesao', subscription_tier='site')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome=slug.replace('-', ' ').title(),
                           endereco='Praça do Coco, Barão Geraldo'))
    for nome, categoria, imagem in produtos:
        session.add(ProdutoSite(restaurant_id=r.id, nome=nome, categoria=categoria,
                                imagem=imagem, ativo=True))
    session.commit()
    return r


def _get(client, caminho):
    return client.get(caminho, headers={'Host': PRODUTO})


def test_pagina_da_subcategoria_lista_produtos_de_varios_expositores(client, session):
    _artesao(session, 'barro-bom', ('Vaso grande', 'Vasos de cerâmica', 'img/a.jpg'))
    _artesao(session, 'mao-na-massa', ('Prato fundo', 'Cerâmica', 'img/b.jpg'),
             ('Brinco azul', 'Bijuteria', 'img/c.jpg'))
    _artesao(session, 'fios-da-ana', ('Urso', 'Amigurumi', 'img/d.jpg'))

    resp = _get(client, '/feira/artesanato/ceramica')
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert '<h1>Cerâmica na Feira</h1>' in html
    assert 'Vaso grande' in html and 'Prato fundo' in html
    assert 'Brinco azul' not in html and 'Urso' not in html
    assert '/feira/artesanato/ceramica"' in html            # canonical da própria página
    assert 'noindex' not in html


def test_categoria_mostra_atalhos_so_das_subcategorias_com_produto(client, session):
    _artesao(session, 'barro-bom', ('Vaso', 'Cerâmica', 'img/a.jpg'))

    html = _get(client, '/feira/artesanato').get_data(as_text=True)
    assert 'href="/feira/artesanato/ceramica"' in html
    assert 'href="/feira/artesanato/macrame"' not in html


def test_subcategoria_de_outra_categoria_ou_inventada_da_404(client, session):
    assert _get(client, '/feira/joias/ceramica').status_code == 404
    assert _get(client, '/feira/artesanato/nao-existe').status_code == 404


def test_subcategoria_sem_produto_existe_mas_nao_indexa(client, session):
    html = _get(client, '/feira/artesanato/macrame').get_data(as_text=True)
    assert 'noindex,follow' in html
    assert 'Ninguém cadastrou' in html


def test_sitemap_traz_subcategorias_com_produto_e_fotos_do_expositor(client, session):
    _artesao(session, 'barro-bom', ('Vaso', 'Cerâmica', 'https://x.blob.test/vaso.jpg'),
             ('Prato', 'Cerâmica', 'img/prato.jpg'))

    resp = _get(client, '/sitemap.xml')
    raiz = ET.fromstring(resp.data)                          # XML válido
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9',
          'image': 'http://www.google.com/schemas/sitemap-image/1.1'}
    urls = {u.findtext('s:loc', namespaces=ns): u for u in raiz.findall('s:url', ns)}

    assert f'https://{PRODUTO}/feira/artesanato/ceramica' in urls
    assert f'https://{PRODUTO}/feira/artesanato/macrame' not in urls
    assert not any('/bar/barro-bom' in u for u in urls)

    expositor = urls[f'https://{PRODUTO}/expositor/barro-bom']
    fotos = [i.findtext('image:loc', namespaces=ns) for i in expositor.findall('image:image', ns)]
    assert fotos == ['https://x.blob.test/vaso.jpg', f'https://{PRODUTO}/static/img/prato.jpg']
    # Página da Feira ganha lastmod = edição mais recente de um expositor.
    assert urls[f'https://{PRODUTO}/feira'].findtext('s:lastmod', namespaces=ns)


# ------------------------------------------------------------------ home

def test_home_poe_a_busca_da_feira_e_o_que_tem_em_destaque(client, session):
    _artesao(session, 'barro-bom', ('Vaso', 'Cerâmica', 'img/a.jpg'))

    html = _get(client, '/').get_data(as_text=True)

    busca = html.split('class="hm-busca"')[1].split('</form>')[0]
    assert '<form class="hm-busca" method="get" action="/feira"' in html
    assert 'name="q"' in busca
    assert 'href="/feira/artesanato/ceramica"' in busca            # atalho real
    assert html.index('class="hm-busca"') < html.index('id="expositores"')
    assert 'id="o-que-tem"' in html and 'href="/feira/artesanato"' in html
    assert 'oficio-card' not in html                               # cartões fixos saíram
    assert 'Uma feira com a história do bairro' in html


def test_home_sem_expositor_nao_mostra_secoes_vazias(client, session):
    html = _get(client, '/').get_data(as_text=True)
    assert 'id="o-que-tem"' not in html and 'id="presentes"' not in html
    assert 'class="hm-busca"' in html                              # a busca fica sempre
