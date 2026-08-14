"""Self-serve de criação de bar (`/cadastro`).

Esta rota ficou 500 em produção por um import faltando (`redirect`, `flash`,
`url_for`): o tenant era commitado e o erro estourava logo depois, deixando um
`Restaurante` sem admin e consumindo o slug. Nenhum teste cobria a rota.

O caso que mais importa aqui é o caminho feliz chegar até o redirect — é
exatamente onde quebrava.
"""
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.usuario import Usuario


DADOS = {
    'nome_bar': 'Boteco do Marcão',
    'nome': 'Marcão',
    'email': 'marcao@boteco.com',
    'senha': 'segredo123',
}


def test_get_cadastro_responde(client):
    resp = client.get('/cadastro')
    assert resp.status_code == 200
    assert 'nome_bar' in resp.get_data(as_text=True)


def test_cadastro_cria_tenant_config_e_admin(client, session):
    resp = client.post('/cadastro', data=DADOS)

    # Redirect (e não 500): é a linha que quebrava.
    assert resp.status_code == 302

    rest = Restaurante.query.filter_by(nome='Boteco do Marcão').one()
    assert rest.slug == 'boteco-do-marcao'
    assert SiteConfig.query.filter_by(restaurant_id=rest.id).count() == 1

    admin = Usuario.query.filter_by(email='marcao@boteco.com').one()
    assert admin.tipo == 'admin'
    assert admin.restaurant_id == rest.id


def test_site_do_bar_novo_ja_responde(client, session):
    """Sai do cadastro com endereço público funcionando."""
    client.post('/cadastro', data=DADOS)
    assert client.get('/bar/boteco-do-marcao').status_code == 200


def test_usuario_logado_nao_cadastra_de_novo(client, session):
    """O signup loga automaticamente; quem já está logado vai pro painel."""
    client.post('/cadastro', data=DADOS)
    resp = client.post('/cadastro', data={**DADOS, 'nome_bar': 'Outro Bar'})

    assert resp.status_code == 302
    assert Restaurante.query.filter_by(nome='Outro Bar').first() is None


def test_email_repetido_nao_cria_segundo_tenant(client, session):
    client.post('/cadastro', data=DADOS)
    client.get('/auth/logout')              # senão cai no redirect de já-logado
    antes = Restaurante.query.count()

    resp = client.post('/cadastro', data={**DADOS, 'nome_bar': 'Outro Bar'})

    assert resp.status_code == 200          # re-renderiza o form, não redireciona
    assert Restaurante.query.count() == antes
    assert Restaurante.query.filter_by(nome='Outro Bar').first() is None


def test_dados_invalidos_nao_deixam_tenant_orfao(client, session):
    resp = client.post('/cadastro', data={
        'nome_bar': 'X',            # curto demais
        'nome': '',
        'email': 'nao-e-email',
        'senha': '123',             # curta demais
    })

    assert resp.status_code == 200
    assert Restaurante.query.count() == 0
    assert Usuario.query.count() == 0
    assert SiteConfig.query.count() == 0


def test_tenant_inativo_some_do_ar(client, session):
    """`ativo=False` é o gancho de demo expirada e de plano — precisa dar 404."""
    client.post('/cadastro', data=DADOS)
    rest = Restaurante.query.filter_by(slug='boteco-do-marcao').one()

    rest.ativo = False
    session.commit()

    assert client.get('/bar/boteco-do-marcao').status_code == 404


def test_tenant_com_ativo_nulo_continua_no_ar(client, session):
    """Coluna `ativo` nasceu por ALTER TABLE em prod: linhas antigas têm NULL.
    Tratar NULL como inativo tiraria do ar bares que já funcionam."""
    client.post('/cadastro', data=DADOS)
    rest = Restaurante.query.filter_by(slug='boteco-do-marcao').one()

    rest.ativo = None
    session.commit()

    assert client.get('/bar/boteco-do-marcao').status_code == 200
