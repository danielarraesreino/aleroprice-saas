"""Quem comprou o site é recebido pelo site, não pela gestão de custos.

O bloco de boas-vindas dispara quando o tenant não tem produto nem venda
cadastrada — condição que um bar do plano Site cumpre para sempre, porque ele
nunca vai cadastrar produto. Na prática, o dono abria o painel que acabou de
pagar e era recebido, todo dia, por "destravar o poder da sua gestão
financeira" e um botão de "Importar Primeira Nota Fiscal".
"""
import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario


def _painel(client, session, tier, slug):
    r = Restaurante(nome=f'Bar {tier}', slug=slug)
    r.tipo_conta = 'cliente'
    r.subscription_tier = tier
    session.add(r)
    session.commit()
    u = Usuario(nome='Dono', email=f'dono-{slug}@bar.com.br',
                senha='senha-bem-longa-123', tipo='admin', restaurant_id=r.id)
    session.add(u)
    session.commit()
    with client.session_transaction() as s:
        s['_user_id'] = str(u.id)
    return client.get('/app/index', follow_redirects=True).get_data(as_text=True)


def test_plano_site_nao_e_mandado_importar_nota(client, session):
    html = _painel(client, session, 'site', 'bar-onb-site')

    assert 'Importar Primeira Nota Fiscal' not in html
    assert 'gestão financeira' not in html
    assert 'Importar XML' not in html


def test_plano_site_recebe_os_passos_do_site(client, session):
    html = _painel(client, session, 'site', 'bar-onb-site-2')

    assert 'Seu site já está no ar' in html
    # Os três passos apontam pra onde o dono resolve cada coisa.
    assert '/config-site/' in html
    assert 'Monte o cardápio' in html


def test_plano_pro_continua_com_o_onboarding_de_gestao(client, session):
    """Quem comprou a gestão continua sendo levado a importar a primeira nota."""
    html = _painel(client, session, 'pro', 'bar-onb-pro')

    assert 'Importar Primeira Nota Fiscal' in html
