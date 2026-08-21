"""O menu do painel mostra o que o bar comprou, não o catálogo inteiro.

O painel listava as 14 abas para todo mundo. Quem assina o plano Site — que é o
que se vende de porta em porta — via metade delas levar a uma tela de upgrade:
Pratos, Cardápios, Estoque, Notas Fiscais, Previsão, Desperdício e Custos, que
são o produto de gestão de custos.

Isso não lê como "existe mais produto". Lê como "comprei pela metade", e é a
primeira tela que o dono vê depois de pagar.
"""
import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario

GESTAO = ['Pratos', 'Cardápios', 'Estoque', 'Notas Fiscais', 'Previsão',
          'Desperdício', 'Custos']
SITE = ['Reservas', 'Agenda', 'Promoções', 'Site', 'Conteúdo']


def _logado(client, session, tier, slug):
    """Cria tenant no plano pedido e devolve o HTML do painel dele."""
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


def test_plano_site_nao_ve_o_produto_de_gestao(client, session):
    html = _logado(client, session, 'site', 'bar-plano-site')

    presentes = [i for i in GESTAO if f'>{i}</a>' in html]
    assert not presentes, f'plano Site vendo abas de gestão: {presentes}'


def test_plano_site_ve_tudo_que_comprou(client, session):
    """O corte não pode levar junto o que o bar pagou para ter."""
    html = _logado(client, session, 'site', 'bar-site-completo')

    faltando = [i for i in SITE if f'>{i}</a>' not in html]
    assert not faltando, f'plano Site sem abas que comprou: {faltando}'


def test_plano_pro_ve_a_gestao(client, session):
    html = _logado(client, session, 'pro', 'bar-plano-pro')

    faltando = [i for i in GESTAO if f'>{i}</a>' not in html]
    assert not faltando, f'plano Pro sem abas de gestão: {faltando}'


def test_free_tambem_nao_ve_gestao(client, session):
    """Bar em free (trial vencido, por exemplo) segue sem o produto de gestão."""
    html = _logado(client, session, 'free', 'bar-plano-free')

    presentes = [i for i in GESTAO if f'>{i}</a>' in html]
    assert not presentes, f'plano free vendo abas de gestão: {presentes}'
