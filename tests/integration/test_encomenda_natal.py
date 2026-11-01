"""Natal: encomenda com retirada na feira e Guia de Presentes."""
from datetime import date
from decimal import Decimal

from app.models.modelo_restaurante import Restaurante
from app.models.modelo_sitecontent import ProdutoSite
from app.models.modelo_siteconfig import SiteConfig
from app.models.usuario import Usuario
from app.utils.feira import proximas_retiradas


def _barraca(session, slug='barraca-natal', retirada=False, whatsapp='5519988887777'):
    r = Restaurante(nome='Barraca Natal', slug=slug, tipo_negocio='artesao', subscription_tier='site')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Barraca Natal', whatsapp=whatsapp,
                           retirada_na_feira=retirada, retirada_antecedencia=3))
    session.add_all([
        ProdutoSite(restaurant_id=r.id, nome='Geleia', preco=Decimal('25'), imagem='img/g.jpg'),
        ProdutoSite(restaurant_id=r.id, nome='Cesta', preco=Decimal('100'), imagem='img/c.jpg'),
        ProdutoSite(restaurant_id=r.id, nome='Tender', preco=Decimal('180'), imagem='img/t.jpg'),
        ProdutoSite(restaurant_id=r.id, nome='Sem preço', imagem='img/s.jpg'),
    ])
    session.commit()
    return r


def test_proximas_retiradas_respeita_o_prazo():
    # Quarta 02/12/2026 com 2 dias: sexta é o mínimo, então sábado 05 e domingo 06.
    datas = proximas_retiradas(date(2026, 12, 2), 2, quantas=4)
    assert datas == [date(2026, 12, 5), date(2026, 12, 6), date(2026, 12, 12), date(2026, 12, 13)]
    # Sexta com 2 dias: domingo é o primeiro.
    assert proximas_retiradas(date(2026, 12, 4), 2, quantas=1) == [date(2026, 12, 6)]
    # Sábado sem prazo: o próprio sábado.
    assert proximas_retiradas(date(2026, 12, 5), 0, quantas=1) == [date(2026, 12, 5)]


def test_sacola_so_oferece_retirada_quando_ligada(client, session):
    _barraca(session, slug='sem-retirada')
    html = client.get('/expositor/sem-retirada').get_data(as_text=True)
    assert 'pedido-retirada' not in html.split('<script')[0]
    _barraca(session, slug='com-retirada', retirada=True)
    html = client.get('/expositor/com-retirada').get_data(as_text=True)
    assert 'id="pedido-retirada" data-antecedencia="3"' in html
    assert 'Retirada na feira: ' in html
    assert 'class="btn pedir-link" id="pedido-enviar"' in html


def test_painel_liga_retirada_e_mostra_datas(client, session):
    r = _barraca(session, slug='painel-natal')
    session.add(Usuario(nome='Dona', email='dona.natal@x.com', senha='segredo123', tipo='admin',
                        restaurant_id=r.id))
    session.commit()
    client.post('/auth/login', data={'email': 'dona.natal@x.com', 'senha': 'segredo123'})
    resp = client.post('/config-site/encomendas',
                       data={'retirada_na_feira': '1', 'retirada_antecedencia': '5'})
    assert resp.status_code == 302
    cfg = SiteConfig.query.filter_by(restaurant_id=r.id).first()
    assert cfg.retirada_na_feira is True and cfg.retirada_antecedencia == 5
    html = client.get('/config-site/encomendas').get_data(as_text=True)
    assert 'checked' in html and ('Sábado, ' in html or 'Domingo, ' in html)
    client.post('/config-site/encomendas', data={'retirada_antecedencia': 'xx'})
    cfg = SiteConfig.query.filter_by(restaurant_id=r.id).first()
    assert cfg.retirada_na_feira is False and cfg.retirada_antecedencia == 2


def test_guia_de_presentes_separa_por_faixa(client, session):
    # Geleia 25, Cesta 100, Tender 180.
    _barraca(session, slug='guia-natal')
    html = client.get('/presentes').get_data(as_text=True)
    assert 'Guia de Presentes da Feira' in html
    trecho = lambda a, b=None: html.split(f'id="{a}"')[1].split(f'id="{b}"')[0] if b else html.split(f'id="{a}"')[1]
    assert 'Geleia' in trecho('ate-30', 'ate-60')
    assert 'Cesta' in trecho('ate-120', 'acima-120')
    assert 'Tender' in trecho('acima-120')
    assert 'Sem preço' not in html
    assert '/expositor/guia-natal#produtos' in html


def test_cesta_ganha_destaque_no_topo(client, session):
    _barraca(session, slug='cesta-natal')
    html = client.get('/presentes').get_data(as_text=True)
    destaque = html.split('id="cestas"')[1].split('id="ate-30"')[0]
    assert 'Cesta' in destaque and 'Geleia' not in destaque


def test_pagina_por_faixa(client, session):
    _barraca(session, slug='faixa-natal')
    resp = client.get('/presentes/ate-30')
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'Presentes de Natal até R$ 30' in html
    assert 'Geleia' in html and 'Tender' not in html
    assert '/presentes/ate-30"' in html  # canonical da própria faixa
    assert client.get('/presentes/ate-999').status_code == 404


def test_eh_cesta():
    from types import SimpleNamespace as P
    from app.utils.feira import eh_cesta
    assert eh_cesta(P(nome='Cesta de Natal', categoria=None))
    assert eh_cesta(P(nome='Geleia', categoria='Kits'))
    assert eh_cesta(P(nome='Caixinha de doces', categoria=''))
    assert not eh_cesta(P(nome='Geleia de amora', categoria='Doces'))


def test_presentes_no_sitemap(client, session):
    xml = client.get('/sitemap.xml').get_data(as_text=True)
    assert '/presentes' in xml and '/presentes/ate-30' in xml and '/presentes/acima-120' in xml
