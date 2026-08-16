"""O preço do prato, do formulário do dono até o site no ar.

`test_campo.py` cobre a outra porta (o vendedor, pelo celular) e
`test_landing_render.py` cobre a saída nos 6 modelos. Aqui é o caminho do dono
sentado no painel: `/conteudo/cardapio`.

O que não pode regredir, em uma frase: **um cardápio sem preço não anuncia
preço**. `moeda_br` devolve "R$ 0,00" quando recebe None — se alguém aplicar o
filtro sem checar antes, ou gravar 0 no lugar de NULL, o bar passa a oferecer
comida de graça no próprio site e no resultado do Google. É por isso que zero,
vazio e lixo terminam todos no mesmo lugar: NULL.
"""
from decimal import Decimal

import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import DishCard
from app.models.usuario import Usuario


@pytest.fixture
def dono(session):
    """Bar com plano `site` (o CRUD de conteúdo é gated por plano) e seu dono."""
    r = Restaurante(nome='Bar do Preço', slug='bar-do-preco',
                    subscription_tier='site', subscription_status='active')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar do Preço',
                           whatsapp='5519999990000', vibe='boteco'))
    session.add(Usuario(nome='Dona', email='dona@bardopreco.com', senha='segredo123',
                        tipo='admin', restaurant_id=r.id))
    session.commit()
    return r


def entrar(client):
    return client.post('/auth/login',
                       data={'email': 'dona@bardopreco.com', 'senha': 'segredo123'})


def criar_prato(client, **campos):
    dados = {'nome': 'Croquete', 'descricao': 'O xodó da casa.'}
    dados.update(campos)
    return client.post('/conteudo/cardapio/novo', data=dados, follow_redirects=False)


# ------------------------------------------------------------------ gravação

@pytest.mark.parametrize('digitado', ['18,50', '18.50', 'R$ 18,50'])
def test_as_tres_grafias_gravam_o_mesmo_preco(client, session, dono, digitado):
    entrar(client)

    criar_prato(client, preco=digitado)

    prato = DishCard.query.filter_by(restaurant_id=dono.id).one()
    assert prato.preco == Decimal('18.50'), digitado


def test_preco_gravado_aparece_no_site(client, session, dono):
    entrar(client)

    criar_prato(client, preco='18,50')

    corpo = client.get('/bar/bar-do-preco').get_data(as_text=True)
    assert 'Croquete' in corpo
    assert 'R$ 18,50' in corpo
    # Vírgula na tela, ponto no grafo — o mesmo número nas duas notações.
    assert '"price":"18.50"' in corpo
    assert '"priceCurrency":"BRL"' in corpo


def test_centavo_nao_se_perde(client, session, dono):
    """O motivo de `Numeric` e não `Float`: 18,10 em binário vira
    18.099999999999998, e esse é o número que iria pro card e pro Google."""
    entrar(client)

    criar_prato(client, preco='18,10')

    assert DishCard.query.filter_by(restaurant_id=dono.id).one().preco == Decimal('18.10')
    assert 'R$ 18,10' in client.get('/bar/bar-do-preco').get_data(as_text=True)


# ------------------------------------------------------- a ausência de preço

@pytest.mark.parametrize('digitado', ['', '   ', '0', '0,00', 'sob consulta'])
def test_o_que_nao_e_preco_grava_null_e_some_da_tela(client, session, dono, digitado):
    entrar(client)

    criar_prato(client, preco=digitado)

    prato = DishCard.query.filter_by(restaurant_id=dono.id).one()
    assert prato.preco is None, repr(digitado)

    corpo = client.get('/bar/bar-do-preco').get_data(as_text=True)
    assert 'Croquete' in corpo, 'o prato sumiu junto com o preço'
    assert 'R$' not in corpo, f'{digitado!r} virou cifrão na tela'
    assert '"offers"' not in corpo, f'{digitado!r} virou Offer no JSON-LD'


def test_prato_sem_preco_nao_bloqueia_o_cadastro(client, session, dono):
    """Preço não é obrigatório: forçar um número faria o dono digitar 0."""
    entrar(client)

    resp = criar_prato(client)

    assert resp.status_code == 302
    assert DishCard.query.filter_by(restaurant_id=dono.id).count() == 1


# ------------------------------------------------------------------- edição

def test_apagar_o_campo_limpa_o_preco(client, session, dono):
    """Baixar o preço é comum; tirar o preço do site também precisa funcionar."""
    entrar(client)
    criar_prato(client, preco='18,50')
    prato = DishCard.query.filter_by(restaurant_id=dono.id).one()

    client.post(f'/conteudo/cardapio/{prato.id}/editar',
                data={'nome': 'Croquete', 'preco': ''})

    session.refresh(prato)
    assert prato.preco is None
    assert 'R$' not in client.get('/bar/bar-do-preco').get_data(as_text=True)


def test_formulario_de_edicao_devolve_o_preco_em_br(client, session, dono):
    """O valor volta como "18,50" (sem R$, sem separador de milhar) pra que
    salvar de novo sem tocar no campo devolva exatamente o mesmo número."""
    entrar(client)
    criar_prato(client, preco='18,50')
    prato = DishCard.query.filter_by(restaurant_id=dono.id).one()

    corpo = client.get(f'/conteudo/cardapio/{prato.id}/editar').get_data(as_text=True)
    assert 'value="18,50"' in corpo

    client.post(f'/conteudo/cardapio/{prato.id}/editar',
                data={'nome': 'Croquete', 'preco': '18,50'})
    session.refresh(prato)
    assert prato.preco == Decimal('18.50')


# -------------------------------------------------------------- multi-tenant

def test_preco_de_um_bar_nao_vaza_pro_outro(client, session, dono):
    """O filtro por `restaurant_id` é manual em todo o app — inclusive aqui."""
    entrar(client)
    criar_prato(client, preco='18,50')

    outro = Restaurante(nome='Bar Vizinho', slug='bar-vizinho')
    session.add(outro)
    session.commit()
    session.add(SiteConfig(restaurant_id=outro.id, nome='Bar Vizinho'))
    session.add(DishCard(restaurant_id=outro.id, nome='Pastel', ordem=0, ativo=True))
    session.commit()

    corpo = client.get('/bar/bar-vizinho').get_data(as_text=True)
    assert 'Pastel' in corpo
    assert 'R$ 18,50' not in corpo, 'o preço do vizinho vazou'
    assert 'R$' not in corpo
