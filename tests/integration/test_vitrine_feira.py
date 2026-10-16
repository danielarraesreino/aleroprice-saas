"""A vitrine da home só mostra barraca cujo /bar/<slug> abre.

A lista sai dos leads versionados, mas quem decide o que está no ar é o banco.
Quando o prazo das prévias passou, a home seguiu anunciando todas as barracas e
cada link dava 404.
"""
from datetime import date, timedelta

from app.models.modelo_restaurante import Restaurante

SLUG = 'emporio-do-nono'   # lead real de Barão, com nota, capa e endereço


def _demo(session, expira_em):
    r = Restaurante(nome='Empório do Nono', slug=SLUG,
                    tipo_conta='demo', demo_expira_em=expira_em)
    session.add(r)
    session.commit()
    return r


def test_barraca_sem_tenant_no_banco_nao_aparece(client, session):
    assert f'/bar/{SLUG}' not in client.get('/').get_data(as_text=True)


def test_barraca_com_previa_no_ar_aparece_e_abre(client, session):
    _demo(session, date.today() + timedelta(days=30))
    assert f'/bar/{SLUG}' in client.get('/').get_data(as_text=True)
    assert client.get(f'/bar/{SLUG}').status_code == 200


def test_prazo_vencido_nao_tira_do_ar(client, session):
    """Não existe mais vencimento automático: só o botão do Modo Campo tira."""
    _demo(session, date.today() - timedelta(days=1))
    assert f'/bar/{SLUG}' in client.get('/').get_data(as_text=True)
    assert client.get(f'/bar/{SLUG}').status_code == 200


def test_barraca_desligada_sai_da_vitrine(client, session):
    r = _demo(session, None)
    r.ativo = False
    session.commit()
    assert f'/bar/{SLUG}' not in client.get('/').get_data(as_text=True)
    assert client.get(f'/bar/{SLUG}').status_code == 404
