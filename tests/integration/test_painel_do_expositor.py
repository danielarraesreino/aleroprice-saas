"""Painel do expositor: início com o que já foi feito, menu e "Seus números" sem coisa de bar."""
from decimal import Decimal

import pytest

from app import create_app, db

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import ProdutoSite
from app.models.usuario import Usuario


def _logado(client, session, slug, tipo='artesao', **cfg):
    r = Restaurante(nome=slug, slug=slug, subscription_tier='site',
                    subscription_status='active', tipo_negocio=tipo)
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome=slug, **cfg))
    session.add(Usuario(nome='Dona', email=f'dona@{slug}.com', senha='senha-bem-longa',
                        tipo='admin', restaurant_id=r.id))
    session.commit()
    with client.session_transaction() as s:
        s['_user_id'] = str(Usuario.query.filter_by(restaurant_id=r.id).one().id)
    return r


@pytest.fixture(scope='module')
def app_site():
    """O produto como roda em produção (gestão desligada): é onde o painel inicial aparece."""
    app = create_app('testing_site')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_inicio_marca_o_que_ja_foi_feito(app_site):
    cliente = app_site.test_client()
    with app_site.app_context():
        r = Restaurante(nome='Madeira Início', slug='madeira-inicio', subscription_tier='site',
                        subscription_status='active', tipo_negocio='artesao')
        db.session.add(r)
        db.session.commit()
        db.session.add(SiteConfig(restaurant_id=r.id, nome='Madeira', whatsapp='5519992359917',
                                  hero_foto='https://blob.test/capa.jpg'))
        db.session.add_all([ProdutoSite(restaurant_id=r.id, nome='Tábua', preco=Decimal('80'), ativo=True),
                            ProdutoSite(restaurant_id=r.id, nome='Vela', ativo=True)])
        u = Usuario(nome='Dona', email='dona@madeira-inicio.com', senha='senha-bem-longa',
                    tipo='admin', restaurant_id=r.id)
        db.session.add(u)
        db.session.commit()
        uid = u.id
    with cliente.session_transaction() as s:
        s['_user_id'] = str(uid)
    html = cliente.get('/app/').get_data(as_text=True)
    assert '<strong>2 de 5</strong>' in html
    assert '1 de 2 com preço' in html
    assert 'Estou na feira hoje' in html and 'Ver meu site' in html
    assert 'Seu site já está no ar' not in html


def test_menu_do_expositor_tem_cinco_itens_claros(client, session):
    _logado(client, session, 'madeira-menu')
    html = client.get('/app/').get_data(as_text=True)
    for nome in ('Início', 'Produtos', 'Meu site', 'Encomendas', 'Divulgar'):
        assert f'>{nome}</a>' in html
    assert '>Conteúdo</a>' not in html and '>Dashboard</a>' not in html


def test_menu_do_bar_segue_igual(client, session):
    _logado(client, session, 'bar-menu', tipo='bar')
    html = client.get('/app/').get_data(as_text=True)
    assert '>Conteúdo</a>' in html and '>Reservas</a>' in html and '>Divulgar</a>' not in html


def test_numeros_do_expositor_nao_fala_de_reserva(client, session):
    _logado(client, session, 'madeira-numeros')
    assert ' reservas em ' not in client.get('/config-site/numeros').get_data(as_text=True)


def test_site_do_expositor_em_tres_blocos_sem_campo_de_bar(client, session):
    _logado(client, session, 'madeira-form')
    html = client.get('/config-site/').get_data(as_text=True)
    for bloco in ('Fotos', 'Sobre a barraca', 'Textos do seu site', 'Contato e Feira'):
        assert bloco in html
    for de_bar in ('Alertas de Reservas no WhatsApp', 'Chamada de topo', 'Selo de avaliações', 'Hamburgueria', 'Bar do Ze'):
        assert de_bar not in html
    assert 'Salvar meu site' in html
