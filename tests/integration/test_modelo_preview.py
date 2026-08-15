"""Prévia de modelo pela URL: `?modelo=<x>` mostra, mas não decide.

É assim que o vendedor abre as 6 opções de layout na frente do dono do bar, na
mesa, sem tocar no site que está no ar. A regra que importa: a query string
NUNCA grava. Quem grava é o dono, depois, no painel.
"""
import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.utils.modelos import MODELOS


@pytest.fixture
def bar(session):
    r = Restaurante(nome='Bar do Ze', cnpj='33333333000193',
                    slug='bar-do-ze-modelo', subscription_tier='site')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar do Ze', modelo='classico'))
    session.commit()
    return r


def _modelo_no_banco(rid):
    return SiteConfig.query.filter_by(restaurant_id=rid).first().modelo


@pytest.mark.parametrize('modelo', [m for m in MODELOS if m != 'classico'])
def test_preview_nao_grava_no_banco(client, session, bar, modelo):
    resp = client.get(f'/bar/{bar.slug}?modelo={modelo}')

    assert resp.status_code == 200
    session.expire_all()
    assert _modelo_no_banco(bar.id) == 'classico'


def test_modelo_invalido_na_query_nao_quebra_nem_grava(client, session, bar):
    """Link torto (ou curioso) não pode derrubar o site do bar."""
    resp = client.get(f'/bar/{bar.slug}?modelo=nao-existe')

    assert resp.status_code == 200
    session.expire_all()
    assert _modelo_no_banco(bar.id) == 'classico'


def test_modelo_salvo_desconhecido_cai_no_classico(client, session, bar):
    """Fallback silencioso: modelo removido do catálogo não tira o site do ar."""
    cfg = SiteConfig.query.filter_by(restaurant_id=bar.id).first()
    cfg.modelo = 'modelo-que-foi-embora'
    session.commit()

    resp = client.get(f'/bar/{bar.slug}')

    assert resp.status_code == 200
    assert 'Bar do Ze' in resp.get_data(as_text=True)


def test_site_sem_query_continua_no_modelo_salvo(client, bar):
    resp = client.get(f'/bar/{bar.slug}')

    assert resp.status_code == 200
    assert 'Bar do Ze' in resp.get_data(as_text=True)
