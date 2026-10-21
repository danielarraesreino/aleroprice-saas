"""Mapa da Feira, "na feira hoje" e busca de produtos (/feira)."""
import json
import re
from datetime import date, datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.models.modelo_sitecontent import ProdutoSite
from app.models.usuario import Usuario
from app.utils import feira as fe


def _tenant(session, slug, cnpj, tipo='bar', lat=None, lng=None, tier='site', **cfg):
    r = Restaurante(nome=slug, slug=slug, cnpj=cnpj, tipo_negocio=tipo, subscription_tier=tier)
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome=cfg.pop('nome', slug), lat=lat, lng=lng, **cfg))
    session.commit()
    return r


def _produto(session, r, nome, imagem='img/berga/tender.jpg', **kw):
    p = ProdutoSite(restaurant_id=r.id, nome=nome, imagem=imagem, **kw)
    session.add(p)
    session.commit()
    return p


@pytest.fixture
def operador(session):
    base = Restaurante(nome='Alero (operador)', slug='alero')
    session.add(base)
    session.commit()
    session.add(Usuario(nome='Vendedor', email='vendedor@alero.com', senha='segredo123',
                        tipo='superadmin', restaurant_id=base.id))
    session.commit()


def _entrar(client, email='vendedor@alero.com', senha='segredo123'):
    return client.post('/auth/login', data={'email': email, 'senha': senha, 'lembrar': '1'})


# ------------------------------------------------------------ utilitários

def test_coordenada_valida_aceita_barao_e_recusa_lixo():
    assert fe.coordenada_valida('-22.8226', '-47.0820') == (-22.8226, -47.0820)
    assert fe.coordenada_valida('-22,8226', '-47,0820') == (-22.8226, -47.0820)  # vírgula
    for ruim in (('0', '0'), ('-22.8', '10'), ('abc', '-47'), (None, None), ('-30', '-47.08')):
        assert fe.coordenada_valida(*ruim) is None


def test_hoje_usa_o_fuso_de_sao_paulo_e_nao_utc():
    # Sábado 23h30 em São Paulo já é domingo em UTC.
    sabado_noite_sp = datetime(2026, 10, 24, 23, 30, tzinfo=timezone(timedelta(hours=-3)))
    assert fe.hoje_br(sabado_noite_sp) == date(2026, 10, 24)
    assert sabado_noite_sp.astimezone(timezone.utc).date() == date(2026, 10, 25)


def test_na_feira_vale_so_no_dia(session):
    r = _tenant(session, 'banca-a', '70000000000170')
    cfg = r.site_config
    assert fe.alternar_na_feira(cfg) is True and cfg.na_feira_em == fe.hoje_br()
    assert fe.alternar_na_feira(cfg) is False and cfg.na_feira_em is None
    cfg.na_feira_em = fe.hoje_br() - timedelta(days=1)         # ontem não conta
    assert fe.expositores(hoje=fe.hoje_br()) == []             # (bar sem pino também não entra)


# ------------------------------------------------------------ página /feira

def test_feira_vazia_tem_estado_vazio_e_nao_quebra(client, session):
    corpo = client.get('/feira').get_data(as_text=True)
    assert 'Expositores da Feira' in corpo
    assert 'Ainda não há expositores' in corpo
    assert 'id="mapa-feira"' not in corpo


def test_lista_so_artesao_ou_bar_com_ponto(client, session):
    _tenant(session, 'artesa', '70000000000171', tipo='artesao', nome='Ateliê Teste')
    _tenant(session, 'bar-com-pino', '70000000000172', lat=-22.8227, lng=-47.0821, nome='Bar Com Pino')
    _tenant(session, 'bar-sem-pino', '70000000000173', nome='Bar Sem Pino')
    corpo = client.get('/feira').get_data(as_text=True)
    assert 'Ateliê Teste' in corpo and 'Bar Com Pino' in corpo
    assert 'Bar Sem Pino' not in corpo


def test_mapa_recebe_so_quem_tem_coordenada(client, session):
    _tenant(session, 'artesa2', '70000000000174', tipo='artesao', nome='Sem Pino')
    _tenant(session, 'com-pino', '70000000000175', tipo='artesao', lat=-22.8230, lng=-47.0825,
            ponto_na_feira='Barraca 12', nome='Com Pino')
    corpo = client.get('/feira').get_data(as_text=True)
    assert 'id="mapa-feira"' in corpo
    pontos = json.loads(re.search(r'var pontos = (\[.*?\]);', corpo, re.S).group(1))
    assert [p['nome'] for p in pontos] == ['Com Pino']
    assert pontos[0]['lat'] == -22.8230 and pontos[0]['ponto'] == 'Barraca 12'
    assert 'Onde:</strong> Barraca 12' in corpo        # alternativa em texto ao mapa


def test_filtros_de_tipo_e_hoje(client, session):
    _tenant(session, 'a-art', '70000000000176', tipo='artesao', nome='Artesã Hoje',
            na_feira_em=fe.hoje_br())
    _tenant(session, 'b-art', '70000000000177', tipo='artesao', nome='Artesã Outro Dia',
            na_feira_em=fe.hoje_br() - timedelta(days=7))
    _tenant(session, 'c-bar', '70000000000178', lat=-22.8227, lng=-47.0821, nome='Bar Pino')
    so_art = client.get('/feira?tipo=artesao').get_data(as_text=True)
    assert 'Artesã Hoje' in so_art and 'Bar Pino' not in so_art
    hoje = client.get('/feira?hoje=1').get_data(as_text=True)
    assert 'Artesã Hoje' in hoje and 'Artesã Outro Dia' not in hoje and 'Bar Pino' not in hoje
    assert '1 expositor avisou' in client.get('/feira').get_data(as_text=True)


def test_busca_de_produto_ignora_acento_e_so_traz_produto_com_foto(client, session):
    r = _tenant(session, 'charcu', '70000000000179', tipo='artesao', nome='Charcutaria Teste')
    _produto(session, r, 'Linguiça Defumada', categoria='Linguiças')
    _produto(session, r, 'Linguiça Sem Foto', imagem=None)
    corpo = client.get('/feira?q=linguica').get_data(as_text=True)
    assert 'Linguiça Defumada' in corpo and 'Linguiça Sem Foto' not in corpo
    assert 'Charcutaria Teste' in corpo and '#produtos' in corpo
    assert 'noindex' in corpo                           # resultado de busca não indexa


def test_busca_sem_resultado_diz_isso_e_nao_quebra(client, session):
    corpo = client.get('/feira?q=zzzzzz').get_data(as_text=True)
    assert 'Nenhum produto com' in corpo


def test_busca_escapa_html_digitado(client, session):
    corpo = client.get('/feira?q=<script>alert(1)</script>').get_data(as_text=True)
    assert '<script>alert(1)</script>' not in corpo


def test_feira_no_sitemap_e_no_topo(client, session):
    assert '/feira</loc>' in client.get('/sitemap.xml').get_data(as_text=True)
    assert 'href="/feira"' in client.get('/memoria').get_data(as_text=True)


# ------------------------------------------------------------ Modo Campo

def test_operador_grava_ponto_e_coordenada(client, session, operador):
    r = _tenant(session, 'banca-campo', '70000000000180', tipo='artesao')
    _entrar(client)
    resp = client.post(f'/campo/{r.slug}/ponto', data={
        'ponto_na_feira': 'Barraca 7, perto do palco', 'lat': '-22.822700', 'lng': '-47.082100'})
    assert resp.status_code == 302
    cfg = SiteConfig.query.filter_by(restaurant_id=r.id).first()
    assert cfg.ponto_na_feira == 'Barraca 7, perto do palco'
    assert (cfg.lat, cfg.lng) == (-22.8227, -47.0821)


def test_ponto_fora_de_campinas_e_recusado_e_nao_apaga_o_anterior(client, session, operador):
    r = _tenant(session, 'banca-campo2', '70000000000181', tipo='artesao', lat=-22.8227, lng=-47.0821)
    _entrar(client)
    client.post(f'/campo/{r.slug}/ponto', data={'lat': '0', 'lng': '0'})
    cfg = SiteConfig.query.filter_by(restaurant_id=r.id).first()
    assert (cfg.lat, cfg.lng) == (-22.8227, -47.0821)


def test_so_operador_mexe_no_ponto(client, session):
    r = _tenant(session, 'banca-campo3', '70000000000182', tipo='artesao')
    assert client.post(f'/campo/{r.slug}/ponto', data={'lat': '-22.82', 'lng': '-47.08'}).status_code in (302, 401, 403, 404)
    assert SiteConfig.query.filter_by(restaurant_id=r.id).first().lat is None


def test_campo_mostra_o_bloco_de_ponto(client, session, operador):
    r = _tenant(session, 'banca-campo4', '70000000000183', tipo='artesao')
    _entrar(client)
    corpo = client.get(f'/campo/{r.slug}').get_data(as_text=True)
    assert 'id="btn-gps"' in corpo and 'name="ponto_na_feira"' in corpo


# ------------------------------------------------------------ painel do dono

def test_dono_avisa_que_esta_na_feira_hoje(client, session):
    r = _tenant(session, 'banca-dono', '70000000000184', tipo='artesao')
    session.add(Usuario(nome='Dona', email='dona@banca.com', senha='SenhaBoa123',
                        tipo='admin', restaurant_id=r.id))
    session.commit()
    _entrar(client, 'dona@banca.com', 'SenhaBoa123')
    client.post('/config-site/na-feira')
    assert SiteConfig.query.filter_by(restaurant_id=r.id).first().na_feira_em == fe.hoje_br()
    corpo = client.get('/config-site/').get_data(as_text=True)
    assert 'Tirar o aviso' in corpo
    assert 'name="modelo"' in corpo and 'value="atelie"' in corpo   # modelos de artesão...
    assert 'value="craft"' not in corpo                           # ...e não os de bar
    client.post('/config-site/na-feira')
    assert SiteConfig.query.filter_by(restaurant_id=r.id).first().na_feira_em is None


# ------------------------------------------------------------ SEO

def test_json_ld_do_expositor_ganha_geo_quando_tem_coordenada(client, session):
    from tests.integration.test_hotsite_artesao import _grafo
    r = _tenant(session, 'banca-geo', '70000000000185', tipo='artesao', lat=-22.8227, lng=-47.0821)
    _produto(session, r, 'Peça')
    grafo = _grafo(client.get('/bar/banca-geo').get_data(as_text=True))
    geo = next(n['geo'] for n in grafo if n['@type'] == 'Store')
    assert geo == {'@type': 'GeoCoordinates', 'latitude': -22.8227, 'longitude': -47.0821}
