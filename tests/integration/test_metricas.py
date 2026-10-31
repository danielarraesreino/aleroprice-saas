"""Seus números: beacon de visitas e cliques, painel do cliente e relatório do mês."""
from datetime import date, timedelta
from urllib.parse import unquote

from app.models.modelo_metrica import MetricaDiaria
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.usuario import Usuario
from app.utils import metricas
from app.utils.feira import hoje_br


def _cliente(session, slug='barraca-num'):
    r = Restaurante(nome='Barraca Num', slug=slug, tipo_negocio='artesao')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Barraca Num', whatsapp='19988887777'))
    session.commit()
    return r


def _total(rid, tipo):
    return sum(m.total for m in MetricaDiaria.query.filter_by(restaurant_id=rid, tipo=tipo))


def test_beacon_soma_visita_e_clique(client, session):
    r = _cliente(session)
    for corpo in ('visita', 'visita', 'encomenda', 'mapa'):
        resp = client.post('/m/barraca-num', data=corpo, content_type='text/plain')
        assert resp.status_code == 204
        assert resp.headers['Cache-Control'] == 'no-store'
    assert _total(r.id, 'visita') == 2
    assert _total(r.id, 'encomenda') == 1 and _total(r.id, 'mapa') == 1
    # Uma linha por dia e tipo, não por evento.
    assert MetricaDiaria.query.filter_by(restaurant_id=r.id, tipo='visita').count() == 1


def test_beacon_ignora_tipo_desconhecido_robo_e_slug_inexistente(client, session):
    r = _cliente(session)
    client.post('/m/barraca-num', data='hackeado', content_type='text/plain')
    client.post('/m/barraca-num', data='visita', content_type='text/plain',
                headers={'User-Agent': 'Googlebot/2.1'})
    assert client.post('/m/nao-existe', data='visita').status_code == 204
    assert MetricaDiaria.query.filter_by(restaurant_id=r.id).count() == 0


def test_dono_logado_nao_infla_os_proprios_numeros(auth_client, session, restaurant):
    restaurant.slug = 'meu-bar-num'
    session.commit()
    auth_client.post('/m/meu-bar-num', data='visita', content_type='text/plain')
    assert MetricaDiaria.query.filter_by(restaurant_id=restaurant.id).count() == 0


def test_site_publico_carrega_o_beacon(client, session):
    _cliente(session)
    html = client.get('/bar/barraca-num').get_data(as_text=True)
    assert "'/m/barraca-num'" in html and 'sendBeacon' in html


def test_painel_mostra_numeros_do_mes_so_do_proprio_cliente(auth_client, session, restaurant):
    restaurant.subscription_tier = 'site'
    session.commit()
    outro = _cliente(session, slug='outra-barraca')
    hoje = hoje_br()
    metricas.registrar(restaurant.id, 'visita', hoje)
    metricas.registrar(restaurant.id, 'visita', hoje)
    for _ in range(9):
        metricas.registrar(outro.id, 'whatsapp', hoje)
    html = auth_client.get('/config-site/numeros').get_data(as_text=True)
    assert 'Seus números' in html
    assert 'visitas no seu site' in html
    assert '>2<' in html.replace(' ', '').replace('\n', '')
    assert '>9<' not in html.replace(' ', '').replace('\n', '')


def test_numeros_exige_login(client, session):
    resp = client.get('/config-site/numeros')
    assert resp.status_code == 302 and '/auth/login' in resp.headers['Location']


def test_texto_do_relatorio_so_leva_o_que_aconteceu():
    soma = dict.fromkeys(metricas.TIPOS, 0)
    soma.update(visita=412, encomenda=37)
    texto = metricas.texto_relatorio('Dona Berga', soma, date(2026, 11, 1), reservas=3,
                                     link='https://feiradebarao.com.br/bar/dona-berga')
    assert 'novembro de 2026' in texto
    assert '412 visitas no seu site' in texto and '37 pedidos' in texto
    assert '3 reservas' in texto and 'mapa' not in texto
    assert texto.endswith('https://feiradebarao.com.br/bar/dona-berga')
    vazio = metricas.texto_relatorio('X', dict.fromkeys(metricas.TIPOS, 0), date(2026, 11, 1))
    assert 'pouco movimento' in vazio


def test_mes_anterior():
    assert metricas.mes_anterior(date(2026, 12, 3)) == (date(2026, 11, 1), date(2026, 11, 30))
    assert metricas.mes_anterior(date(2026, 1, 15)) == (date(2025, 12, 1), date(2025, 12, 31))


def test_relatorio_do_operador_abre_whatsapp_do_dono(client, session):
    op = Restaurante(nome='Alero (operador)', slug='alero')
    session.add(op)
    session.commit()
    session.add(Usuario(nome='Vendedor', email='vend.num@alero.com', senha='segredo123',
                        tipo='superadmin', restaurant_id=op.id))
    r = _cliente(session)
    inicio, _ = metricas.mes_anterior()
    metricas.registrar(r.id, 'visita', inicio + timedelta(days=2))
    session.commit()
    client.post('/auth/login', data={'email': 'vend.num@alero.com', 'senha': 'segredo123'})
    html = client.get('/campo/barraca-num/relatorio').get_data(as_text=True)
    assert 'https://wa.me/5519988887777?text=' in html
    texto = unquote(html.split('wa.me/5519988887777?text=')[1].split('"')[0])
    assert '1 visitas no seu site' in texto and 'Barraca Num' in texto


def test_relatorio_e_so_do_operador(auth_client, session):
    _cliente(session)
    assert auth_client.get('/campo/barraca-num/relatorio').status_code == 404
