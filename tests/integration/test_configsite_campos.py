"""Painel do site: campos numéricos aceitam o que o dono digita."""
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.usuario import Usuario


def _logado(client, session, slug):
    r = Restaurante(nome='Barraca Pix', slug=slug, tipo_negocio='artesao', subscription_tier='site')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Barraca Pix'))
    session.add(Usuario(nome='Dona', email=f'{slug}@x.com', senha='segredo123', tipo='admin',
                        restaurant_id=r.id))
    session.commit()
    client.post('/auth/login', data={'email': f'{slug}@x.com', 'senha': 'segredo123'})
    return r


def _salvar(client, r, valor):
    resp = client.post('/config-site/', data={'nome': 'Barraca Pix', 'desconto_pix_pct': valor})
    assert resp.status_code in (200, 302)
    return SiteConfig.query.filter_by(restaurant_id=r.id).first().desconto_pix_pct


def test_desconto_pix_com_porcento_vira_numero(client, session):
    r = _logado(client, session, 'pix-pct')
    assert _salvar(client, r, '5%') == 5
    assert _salvar(client, r, ' 10 % ') == 10
    assert _salvar(client, r, '7,5') == 7
    assert _salvar(client, r, '') is None
