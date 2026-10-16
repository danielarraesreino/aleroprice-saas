"""O produto como roda em produção: site + admin do site, sem a gestão.

Com GESTAO_ATIVA desligada, os blueprints de custos/estoque/NF-e/previsão nem
são registrados. O risco é um `url_for` esquecido num template que continua no
ar virar BuildError (500) na primeira tela do dono — por isso cada plano abre o
painel aqui.
"""
import subprocess
import sys

import pytest

from app import create_app, db
from app.models.modelo_restaurante import Restaurante
from app.models.usuario import Usuario

GESTAO = ['Pratos', 'Cardápios', 'Estoque', 'Notas Fiscais', 'Previsão',
          'Desperdício', 'Custos']


@pytest.fixture(scope='module')
def app_site():
    app = create_app('testing_site')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def cliente(app_site):
    return app_site.test_client()


def _dono(app_site, cliente, tier, slug, tipo_conta='cliente'):
    with app_site.app_context():
        r = Restaurante(nome=f'Bar {slug}', slug=slug, tipo_conta=tipo_conta,
                        subscription_tier=tier)
        db.session.add(r)
        db.session.commit()
        u = Usuario(nome='Dono', email=f'{slug}@bar.com.br',
                    senha='senha-bem-longa-123', tipo='admin', restaurant_id=r.id)
        db.session.add(u)
        db.session.commit()
        uid = u.id
    with cliente.session_transaction() as s:
        s['_user_id'] = str(uid)


@pytest.mark.parametrize('tier,slug,tipo', [
    ('site', 'sg-site', 'cliente'),
    ('pro', 'sg-pro', 'cliente'),
    (None, 'sg-demo', 'demo'),
])
def test_painel_abre_sem_gestao_em_todo_plano(app_site, cliente, tier, slug, tipo):
    _dono(app_site, cliente, tier, slug, tipo)
    resp = cliente.get('/app/index')
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert [i for i in GESTAO if f'>{i}</a>' in html] == []
    assert '/config-site' in html          # a casa do dono é o site


def test_rotas_de_gestao_nao_existem(app_site, cliente):
    _dono(app_site, cliente, 'pro', 'sg-rotas')
    for url in ('/estoque/', '/nfe/', '/pratos/', '/previsao/', '/agentes/',
                '/app/relatorio/pratos'):
        assert cliente.get(url).status_code == 404, url


def test_admin_do_site_e_planos_continuam(app_site, cliente):
    _dono(app_site, cliente, 'site', 'sg-admin')
    for url in ('/config-site/', '/conteudo/', '/app/upgrade', '/bar/sg-admin'):
        assert cliente.get(url, follow_redirects=True).status_code == 200, url


def test_sem_gestao_o_boot_nao_carrega_pandas():
    """É o que tira ~137 MB do deploy e a reinstalação no cold start."""
    codigo = ("import sys; from app import create_app; create_app('testing_site'); "
              "print('pandas' in sys.modules or 'numpy' in sys.modules)")
    saida = subprocess.run([sys.executable, '-c', codigo], capture_output=True,
                           text=True, check=True).stdout.strip().splitlines()[-1]
    assert saida == 'False'
