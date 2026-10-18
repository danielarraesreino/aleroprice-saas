"""Pedir avaliação no Google: link curto contado, QR e mensagem por reserva."""
from datetime import date, timedelta
from urllib.parse import unquote

from app.models.modelo_reserva import Reserva
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig


def _bar(session, slug='bar-aval', place='ChIJ_teste-123'):
    r = Restaurante(nome='Bar Aval', slug=slug)
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar Aval', google_place_id=place))
    session.commit()
    return r


def test_avaliar_conta_e_redireciona_para_o_google(client, session):
    r = _bar(session)
    resp = client.get('/bar/bar-aval/avaliar')
    assert resp.status_code == 302
    assert resp.headers['Location'] == ('https://search.google.com/local/writereview'
                                        '?placeid=ChIJ_teste-123')
    client.get('/bar/bar-aval/avaliar')
    assert SiteConfig.query.filter_by(restaurant_id=r.id).first().cliques_avaliacao == 2


def test_avaliar_sem_place_id_volta_pro_site(client, session):
    _bar(session, slug='bar-sem-id', place=None)
    resp = client.get('/bar/bar-sem-id/avaliar')
    assert resp.status_code == 302 and resp.headers['Location'].endswith('/bar/bar-sem-id')


def test_avaliar_bar_inexistente_404(client, session):
    assert client.get('/bar/nao-existe/avaliar').status_code == 404


def test_painel_salva_place_id_e_recusa_url(auth_client, session, restaurant):
    resp = auth_client.post('/reservas/avaliacoes', data={'google_place_id': 'https://maps.google.com/x'})
    assert resp.status_code == 302
    cfg = SiteConfig.query.filter_by(restaurant_id=restaurant.id).first()
    assert cfg is None or cfg.google_place_id is None
    auth_client.post('/reservas/avaliacoes', data={'google_place_id': ' ChIJabc_123 '})
    assert SiteConfig.query.filter_by(restaurant_id=restaurant.id).first().google_place_id == 'ChIJabc_123'


def test_painel_lista_so_reservas_recentes_do_proprio_bar(auth_client, session, restaurant):
    restaurant.slug = restaurant.slug or 'bar-do-teste'
    session.add(SiteConfig(restaurant_id=restaurant.id, nome='Meu Bar', google_place_id='ChIJmeu'))
    outro = _bar(session, slug='outro-bar')
    ontem = date.today() - timedelta(days=1)
    session.add_all([
        Reserva(nome='Ana Souza', telefone='(19) 99999-1111', data=ontem, hora='20:00',
                restaurant_id=restaurant.id, status='confirmada'),
        Reserva(nome='Velho', telefone='19999992222', data=ontem - timedelta(days=10),
                hora='20:00', restaurant_id=restaurant.id),
        Reserva(nome='Cancelado', telefone='19999993333', data=ontem, hora='21:00',
                restaurant_id=restaurant.id, status='cancelada'),
        Reserva(nome='Cliente Do Outro', telefone='19999994444', data=ontem, hora='20:00',
                restaurant_id=outro.id),
    ])
    session.commit()
    html = auth_client.get('/reservas/avaliacoes').get_data(as_text=True)
    assert 'Ana Souza' in html
    assert 'Velho' not in html and 'Cancelado' not in html and 'Cliente Do Outro' not in html
    assert 'https://wa.me/5519999991111?text=' in html
    texto = unquote(html.split('wa.me/5519999991111?text=')[1].split('"')[0])
    assert 'Oi, Ana!' in texto and '/avaliar' in texto
    assert '<svg' in html  # QR


def test_painel_exige_login(client, session):
    resp = client.get('/reservas/avaliacoes')
    assert resp.status_code == 302 and '/auth/login' in resp.headers['Location']
