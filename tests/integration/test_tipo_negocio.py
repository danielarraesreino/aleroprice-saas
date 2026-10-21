"""tipo_negocio: bares existentes seguem iguais; artesão troca rótulo e schema."""
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_sitecontent import DishCard, ProdutoSite
from app.models.modelo_siteconfig import SiteConfig


def _tenant(session, slug, cnpj, **extra):
    r = Restaurante(nome=slug, cnpj=cnpj, slug=slug, subscription_tier='site', **extra)
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome=slug))
    session.add(DishCard(restaurant_id=r.id, nome='Item', preco=10))
    session.commit()
    return r


def test_default_e_bar(session):
    r = _tenant(session, 'bar-padrao', '33333333000193')
    assert r.tipo_negocio == 'bar'


def test_bar_continua_com_cardapio_e_restaurant(client, session):
    _tenant(session, 'bar-tipo', '44444444000194')
    corpo = client.get('/bar/bar-tipo').get_data(as_text=True)
    assert '>Cardápio</a>' in corpo
    assert '"@type": "Store"' not in corpo and '"@type":"Store"' not in corpo


def test_artesao_troca_rotulo_e_schema(client, session):
    r = _tenant(session, 'atelie-teste', '55555555000195', tipo_negocio='artesao')
    session.add(ProdutoSite(restaurant_id=r.id, nome='Peça', imagem='img/berga/tender.jpg'))
    session.commit()
    corpo = client.get('/bar/atelie-teste').get_data(as_text=True)
    assert '>Produtos</a>' in corpo
    assert '>Cardápio</a>' not in corpo
    assert 'Store' in corpo
