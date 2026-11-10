"""Páginas de categoria da Feira (/feira/<categoria>)."""
from decimal import Decimal

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_sitecontent import ProdutoSite
from app.models.modelo_siteconfig import SiteConfig


def _expositor(session, slug, nome, categoria):
    r = Restaurante(nome=nome, slug=slug, tipo_negocio='artesao', subscription_tier='site')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome=nome, lat=-22.82, lng=-47.08))
    session.add(ProdutoSite(restaurant_id=r.id, nome=f'Peça {nome}', categoria=categoria,
                            preco=Decimal('40'), imagem='img/x.jpg'))
    session.commit()


def test_categoria_filtra_e_tem_titulo_proprio(client, session):
    _expositor(session, 'lili-cer', 'Lili Cerâmicas', 'Cerâmica')
    _expositor(session, 'pao-da-ana', 'Pão da Ana', 'Pão de fermentação natural')
    resp = client.get('/feira/artesanato')
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert '<h1>Artesanato em Barão Geraldo</h1>' in html
    assert '<title>Artesanato em Barão Geraldo: expositores da Feira de Barão</title>' in html
    assert 'Lili Cerâmicas' in html and 'Pão da Ana' not in html
    assert '/feira/artesanato"' in html          # canonical
    assert 'noindex' not in html


def test_categoria_desconhecida_404(client):
    assert client.get('/feira/naoexiste').status_code == 404


def test_sitemap_so_lista_categoria_com_gente(client, session):
    _expositor(session, 'pao-sitemap', 'Pão Sitemap', 'Pão')
    xml = client.get('/sitemap.xml').get_data(as_text=True)
    assert '/feira/comida-artesanal' in xml
    assert '/feira/joias' not in xml


def test_categoria_por_comeco_de_palavra():
    from app.utils.feira import categorias_do_expositor as cats
    e = lambda txt: {'nome': txt, 'descritor': None, 'categorias': []}
    assert cats(e('Afazeres Artesanato')) == ['artesanato']      # não vira "arte"
    assert 'joias' not in cats(e('Biscoito de canela'))           # "anel" dentro de canela
    assert 'arte' in cats(e('Amor em Artes'))
    assert 'plantas' in cats(e('Neto Schmidt Terrários'))


def test_css_e_js_saem_com_versao_e_imagem_nao(app):
    with app.test_request_context():
        from flask import url_for
        assert '?v=' in url_for('static', filename='css/feira.css')
        assert '?v=' not in url_for('static', filename='img/og-feira.jpg')
