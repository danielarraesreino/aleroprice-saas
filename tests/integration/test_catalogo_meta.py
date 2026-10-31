"""Feed do catálogo para a Meta (WhatsApp Business e Instagram) e a tela do painel."""
import csv
import io
from decimal import Decimal

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_sitecontent import DishCard, ProdutoSite
from app.models.modelo_siteconfig import SiteConfig


def _barraca(session, slug='barraca-cat'):
    r = Restaurante(nome='Barraca Cat', slug=slug, tipo_negocio='artesao')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Dona Cat'))
    session.add_all([
        ProdutoSite(restaurant_id=r.id, nome='Copa lombo', descricao='Curada 90 dias',
                    preco=Decimal('89.90'), imagem='img/berga/copa.jpg', ordem=1),
        ProdutoSite(restaurant_id=r.id, nome='Tender', preco=Decimal('120'),
                    imagem='https://blob.example/tender.jpg', sob_encomenda=True, ordem=2),
        ProdutoSite(restaurant_id=r.id, nome='Sem foto', preco=Decimal('10'), ordem=3),
        ProdutoSite(restaurant_id=r.id, nome='Sem preço', imagem='img/x.jpg', ordem=4),
        ProdutoSite(restaurant_id=r.id, nome='Inativo', preco=Decimal('5'), imagem='img/y.jpg',
                    ativo=False, ordem=5),
    ])
    session.commit()
    return r


def _ler(resp):
    return list(csv.DictReader(io.StringIO(resp.get_data(as_text=True))))


def test_feed_leva_so_produto_com_foto_e_preco(client, session):
    r = _barraca(session)
    resp = client.get('/bar/barraca-cat/catalogo.csv')
    assert resp.status_code == 200 and resp.mimetype == 'text/csv'
    itens = _ler(resp)
    assert [i['title'] for i in itens] == ['Copa lombo', 'Tender']
    copa, tender = itens
    assert copa['price'] == '89.90 BRL' and tender['price'] == '120.00 BRL'
    assert copa['availability'] == 'in stock'
    assert tender['availability'] == 'available for order'
    assert copa['description'] == 'Curada 90 dias' and tender['description'] == 'Tender'
    assert copa['image_link'].startswith('https://') and copa['image_link'].endswith('/static/img/berga/copa.jpg')
    assert tender['image_link'] == 'https://blob.example/tender.jpg'
    assert copa['link'].endswith('/bar/barraca-cat') and copa['brand'] == 'Dona Cat'
    assert copa['id'] != tender['id'] and copa['condition'] == 'new'


def test_feed_de_bar_usa_os_pratos(client, session):
    r = Restaurante(nome='Bar Cat', slug='bar-cat')
    session.add(r)
    session.commit()
    session.add(DishCard(restaurant_id=r.id, nome='Croquete', preco=Decimal('32'), imagem='img/c.jpg'))
    session.commit()
    itens = _ler(client.get('/bar/bar-cat/catalogo.csv'))
    assert len(itens) == 1 and itens[0]['title'] == 'Croquete' and itens[0]['id'].startswith('d')


def test_feed_de_slug_inexistente_404(client, session):
    assert client.get('/bar/nao-existe/catalogo.csv').status_code == 404


def test_painel_mostra_endereco_e_o_que_ficou_de_fora(client, session):
    from app.models.usuario import Usuario
    r = _barraca(session)
    r.subscription_tier = 'site'
    session.add(Usuario(nome='Dona', email='dona.cat@x.com', senha='segredo123', tipo='admin',
                        restaurant_id=r.id))
    session.commit()
    client.post('/auth/login', data={'email': 'dona.cat@x.com', 'senha': 'segredo123'})
    html = client.get('/config-site/catalogo').get_data(as_text=True)
    assert '/bar/barraca-cat/catalogo.csv' in html
    assert '2 produtos no catálogo' in html
    assert '2 produtos ficaram de fora porque estão' in html
    assert 'R$ 89,90' in html
