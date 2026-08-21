"""O selo de apoio ao Caminhos só aparece quando o bar pediu.

É uma declaração pública feita em nome do bar — "esta casa apoia" — e por isso
tem três regras que não podem afrouxar: nasce desligado, só o dono liga, e
nunca aparece em prévia comercial. Prévia é de bar que não fechou contrato e
não sabe que existe: pôr uma causa na boca dele seria usar o nome de terceiro
para falar por ele.
"""
import pytest

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.usuario import Usuario

SELO = 'Esta casa apoia'


@pytest.fixture
def bar(session):
    r = Restaurante(nome='Bar do Selo', slug='bar-do-selo')
    r.tipo_conta = 'cliente'
    r.subscription_tier = 'site'
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Bar do Selo'))
    session.commit()
    return r


def _cfg(session, rest):
    return SiteConfig.query.filter_by(restaurant_id=rest.id).first()


def test_nasce_desligado(bar, session, client):
    assert _cfg(session, bar).apoia_caminhos in (False, None)
    assert SELO not in client.get(f'/bar/{bar.slug}').get_data(as_text=True)


def test_ligado_aparece_no_site(bar, session, client):
    _cfg(session, bar).apoia_caminhos = True
    session.commit()

    html = client.get(f'/bar/{bar.slug}').get_data(as_text=True)
    assert SELO in html
    assert 'caminhos-cps.social' in html


def test_previa_nunca_mostra_o_selo(session, client):
    """Bar que ainda não é cliente não declara apoio a nada.

    Mesmo com a coluna ligada no banco — o que pode acontecer numa conversão ou
    numa carga de dados — a prévia não fala em nome de um bar que não pediu.
    """
    r = Restaurante(nome='Bar Prévia', slug='bar-previa')
    r.tipo_conta = 'demo'
    session.add(r)
    session.commit()
    cfg = SiteConfig(restaurant_id=r.id, nome='Bar Prévia')
    cfg.apoia_caminhos = True
    session.add(cfg)
    session.commit()

    assert SELO not in client.get(f'/bar/{r.slug}').get_data(as_text=True)


def test_dono_liga_e_desliga_pelo_painel(bar, session, client):
    u = Usuario(nome='Dono', email='dono@bardoselo.com.br', senha='senha-longa-123',
                tipo='admin', restaurant_id=bar.id)
    session.add(u)
    session.commit()
    with client.session_transaction() as s:
        s['_user_id'] = str(u.id)

    client.post('/config-site/index', data={'apoia_caminhos': '1'})
    assert _cfg(session, bar).apoia_caminhos is True

    # Checkbox desmarcado não é enviado pelo navegador: ausência tem que
    # desligar, e não ser lida como "campo não informado, mantém o que estava".
    client.post('/config-site/index', data={})
    assert _cfg(session, bar).apoia_caminhos is False


@pytest.mark.parametrize('modelo', ['classico', 'craft', 'tradicional',
                                    'autoral', 'noturno', 'brasa'])
def test_todo_modelo_mostra_o_selo(bar, session, client, modelo):
    """Os seis têm rodapés próprios; o selo tem que existir em todos.

    Sem isto, trocar o modelo do site apagaria o apoio sem o dono saber.
    """
    cfg = _cfg(session, bar)
    cfg.apoia_caminhos = True
    cfg.modelo = modelo
    session.commit()

    assert SELO in client.get(f'/bar/{bar.slug}').get_data(as_text=True)
