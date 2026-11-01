"""QR do cardápio no painel do bar: o dono vê e baixa o QR que abre o cardápio."""
import io
from decimal import Decimal

import segno

from app.models.modelo_sitecontent import DishCard


def _com_prato(session, restaurant, slug='bar-do-painel', **extra):
    restaurant.slug = slug
    for k, v in extra.items():
        setattr(restaurant, k, v)
    session.add(DishCard(restaurant_id=restaurant.id, nome='Costela', preco=Decimal('62.00'),
                         ativo=True, ordem=0))
    session.commit()


def test_bar_ve_o_qr_com_a_url_do_cardapio(auth_client, session, restaurant):
    _com_prato(session, restaurant)

    corpo = auth_client.get('/reservas/avaliacoes').get_data(as_text=True)

    assert 'QR do cardápio para a mesa' in corpo
    assert 'https://feiradebarao.com.br/bar/bar-do-painel/cardapio' in corpo
    assert '/reservas/qr-cardapio.svg' in corpo


def test_bar_baixa_o_qr_svg(auth_client, session, restaurant):
    _com_prato(session, restaurant)

    resp = auth_client.get('/reservas/qr-cardapio.svg')

    assert resp.status_code == 200
    assert resp.mimetype == 'image/svg+xml'
    assert 'attachment' in resp.headers['Content-Disposition']
    assert b'<svg xmlns="http://www.w3.org/2000/svg"' in resp.data


def test_qr_acompanha_o_dominio_proprio(auth_client, session, restaurant):
    _com_prato(session, restaurant, dominio='barteste.bar')

    corpo = auth_client.get('/reservas/avaliacoes').get_data(as_text=True)
    baixado = auth_client.get('/reservas/qr-cardapio.svg').data

    url = 'https://barteste.bar/bar/bar-do-painel/cardapio'
    assert url in corpo
    # O arquivo baixado codifica exatamente essa URL.
    esperado = io.BytesIO()
    segno.make(url, error='m').save(esperado, kind='svg', scale=6, border=2,
                                    dark='#000000', light='#ffffff', xmldecl=False)
    assert baixado == esperado.getvalue()


def test_bar_sem_prato_nao_ganha_qr(auth_client, session, restaurant):
    restaurant.slug = 'bar-vazio'
    session.commit()

    corpo = auth_client.get('/reservas/avaliacoes').get_data(as_text=True)

    assert '/reservas/qr-cardapio.svg' not in corpo
    assert 'Cadastre um prato' in corpo


def test_artesao_nao_ve_nem_baixa(auth_client, session, restaurant):
    _com_prato(session, restaurant, tipo_negocio='artesao')

    corpo = auth_client.get('/reservas/avaliacoes').get_data(as_text=True)

    assert 'QR do cardápio' not in corpo
    assert auth_client.get('/reservas/qr-cardapio.svg').status_code == 404
