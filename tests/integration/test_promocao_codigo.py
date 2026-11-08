"""Cupom com código: formulário do dono e exibição no site do bar."""
from app.models.modelo_promocao import Promocao


def _plano_site(restaurant, session):
    restaurant.subscription_tier = 'site'
    session.commit()


def test_dono_cria_promocao_com_codigo_normalizado(auth_client, session, restaurant):
    _plano_site(restaurant, session)
    resp = auth_client.post('/promocoes/nova', data={
        'titulo': 'Chopp em dobro', 'codigo': ' quarta10 ', 'ativo': 'on'})
    assert resp.status_code == 302
    promo = Promocao.query.filter_by(restaurant_id=restaurant.id).one()
    assert promo.codigo == 'QUARTA10'


def test_codigo_invalido_nao_grava_e_avisa(auth_client, session, restaurant):
    _plano_site(restaurant, session)
    resp = auth_client.post('/promocoes/nova', data={
        'titulo': 'Chopp em dobro', 'codigo': 'ab', 'ativo': 'on'})
    assert resp.status_code == 200 and 'de 3 a 20' in resp.get_data(as_text=True)
    assert Promocao.query.filter_by(restaurant_id=restaurant.id).count() == 0


def test_codigo_em_branco_vira_sem_codigo(auth_client, session, restaurant):
    _plano_site(restaurant, session)
    auth_client.post('/promocoes/nova', data={'titulo': 'Happy hour', 'codigo': '', 'ativo': 'on'})
    assert Promocao.query.filter_by(restaurant_id=restaurant.id).one().codigo is None


def test_site_do_bar_mostra_o_codigo_so_de_quem_tem(client, session, restaurant):
    restaurant.slug = 'bar-cupom'
    restaurant.subscription_tier = 'site'
    restaurant.subscription_status = 'active'
    session.commit()
    session.add_all([
        Promocao(restaurant_id=restaurant.id, titulo='Com cupom', ativo=True, codigo='QUARTA10'),
        Promocao(restaurant_id=restaurant.id, titulo='Sem cupom', ativo=True),
    ])
    session.commit()
    html = client.get('/bar/bar-cupom').get_data(as_text=True)
    assert 'QUARTA10' in html and html.count('class="cupom"') == 1
