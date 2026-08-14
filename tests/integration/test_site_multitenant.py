"""Isolamento entre bares no site público.

Antes destes testes o site vazava identidade entre tenants: os fallbacks em
`publico/views.py` eram literalmente os dados do Bar da Vila, então um bar novo
sem SiteConfig nascia com o nome, o endereço, o Instagram e o WhatsApp dele —
e a reserva de um bar tocava o telefone do dono de outro.
"""
import pytest

from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.utils.site_router import gerar_slug, normalizar_host


WHATSAPP_BAR_DA_VILA = '5519999779942'


@pytest.fixture
def bar_da_vila(session):
    r = Restaurante(nome='Bar da Vila', cnpj='11111111000191',
                    slug='bar-da-vila', dominio='bardavila.bar',
                    subscription_tier='site')   # cliente pagante: recebe reserva
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar da Vila',
                           whatsapp=WHATSAPP_BAR_DA_VILA, tema='boteco-ambar'))
    session.commit()
    return r


@pytest.fixture
def bar_novo(session):
    """Cliente novo, ainda sem SiteConfig — o caso que vazava."""
    r = Restaurante(nome='Bar do Ze', cnpj='22222222000192',
                    slug='bar-do-ze', dominio=None,
                    subscription_tier='site')
    session.add(r)
    session.commit()
    return r


def test_bar_novo_nao_herda_identidade_do_bar_da_vila(client, bar_da_vila, bar_novo):
    resp = client.get(f'/bar/{bar_novo.slug}')
    corpo = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert WHATSAPP_BAR_DA_VILA not in corpo
    assert 'Croquete da Bruna' not in corpo
    assert 'barda_vila178' not in corpo          # instagram
    assert 'Madalena Barbosa Ferreira' not in corpo  # endereço
    assert 'Bar do Ze' in corpo                  # cai no Restaurante.nome


def test_reserva_sem_tenant_resolvivel_e_recusada(client, bar_da_vila):
    """Host desconhecido e sem slug: não dá pra saber de qual bar é a reserva.
    Antes, caía no 'primeiro restaurante do banco'."""
    resp = client.post('/reservar', data={
        'nome': 'Fulano', 'telefone': '19999999999',
        'data': '2030-01-01', 'hora': '20:00', 'num_pessoas': '2',
    }, headers={'Host': 'dominio-desconhecido.com'})

    assert resp.status_code == 400
    assert resp.get_json()['ok'] is False


def test_reserva_vai_para_o_bar_do_dominio(client, bar_da_vila, bar_novo):
    resp = client.post('/reservar', data={
        'nome': 'Fulano', 'telefone': '19999999999',
        'data': '2030-01-01', 'hora': '20:00', 'num_pessoas': '2',
    }, headers={'Host': 'bardavila.bar'})

    assert resp.status_code == 200
    dados = resp.get_json()
    assert dados['ok'] is True
    # o link de WhatsApp é o do bar que recebeu a reserva
    assert WHATSAPP_BAR_DA_VILA in dados['wa_url']

    from app.models.modelo_reserva import Reserva
    reserva = Reserva.query.order_by(Reserva.id.desc()).first()
    assert reserva.restaurant_id == bar_da_vila.id


def test_reserva_por_slug_quando_nao_ha_dominio(client, bar_novo):
    """Demo servida em /bar/<slug>: o Host é o do produto, então o form manda o slug."""
    resp = client.post('/reservar', data={
        'nome': 'Fulano', 'telefone': '19999999999',
        'data': '2030-01-01', 'hora': '20:00', 'num_pessoas': '2',
        'slug': bar_novo.slug,
    }, headers={'Host': 'feiradebarao.com.br'})

    assert resp.status_code == 200
    from app.models.modelo_reserva import Reserva
    reserva = Reserva.query.order_by(Reserva.id.desc()).first()
    assert reserva.restaurant_id == bar_novo.id


def test_reserva_de_bar_sem_whatsapp_nao_vaza_numero_de_outro(client, bar_novo):
    """Sem WhatsApp configurado, o retorno não traz link — e nunca o de outro bar."""
    resp = client.post('/reservar', data={
        'nome': 'Fulano', 'telefone': '19999999999',
        'data': '2030-01-01', 'hora': '20:00', 'num_pessoas': '2',
        'slug': bar_novo.slug,
    }, headers={'Host': 'feiradebarao.com.br'})

    assert resp.get_json()['wa_url'] is None


def test_normalizar_host():
    assert normalizar_host('WWW.BarDaVila.bar:5000') == 'bardavila.bar'
    assert normalizar_host('bardavila.bar.') == 'bardavila.bar'
    assert normalizar_host('') == ''


def test_gerar_slug():
    assert gerar_slug('Bar do Zé') == 'bar-do-ze'
    assert gerar_slug('Boteco  da  Esquina!') == 'boteco-da-esquina'
