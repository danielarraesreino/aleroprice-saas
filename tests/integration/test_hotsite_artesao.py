"""Hotsite de artesão (Berga): produtos, schema Product, domínio próprio, /kits."""
import json
import re

from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_sitecontent import ProdutoSite
from app.scripts.seed_berga import SLUG, DOMINIO, IMAGENS, PRODUTOS, semear


def _grafo(corpo):
    bruto = re.search(r'<script type="application/ld\+json">(.*?)</script>', corpo, re.S).group(1)
    return json.loads(bruto)['@graph']


def test_seed_cria_tenant_inativo_e_nao_serve_site(client, session):
    rest, novos = semear()
    assert rest.tipo_negocio == 'artesao' and rest.ativo is False
    assert novos == len(PRODUTOS)
    assert client.get(f'/bar/{SLUG}').status_code == 404


def test_seed_e_idempotente(session):
    semear()
    _, novos = semear()
    assert novos == 0
    assert ProdutoSite.query.count() == len(PRODUTOS)


def test_site_no_ar_mostra_produtos_por_categoria(client, session):
    semear(no_ar=True)
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    assert 'Dona Berga' in corpo
    assert '>Produtos</a>' in corpo and '>Cardápio</a>' not in corpo
    for cat in ("Defumados", "Linguiças", "Maturados", "Conservas", "Kits"):
        assert f'>{cat}</button>' in corpo      # filtro de categoria
    assert 'Sob encomenda' in corpo
    assert 'wa.me/5519991563362' in corpo
    assert 'R$ 0' not in corpo          # sem preço: nunca "R$ 0,00"


def test_json_ld_tem_product_e_nao_menu(client, session):
    semear(no_ar=True)
    grafo = _grafo(client.get(f'/bar/{SLUG}').get_data(as_text=True))
    tipos = [n['@type'] for n in grafo]
    assert 'Store' in tipos and 'Menu' not in tipos
    assert tipos.count('Product') == len(IMAGENS)      # só os que têm foto
    assert all('offers' not in n for n in grafo if n['@type'] == 'Product')  # sem preço


def test_preco_vira_offer(client, session):
    rest, _ = semear(no_ar=True)
    p = ProdutoSite.query.filter_by(restaurant_id=rest.id, nome='Tender').first()
    p.preco = 42.5
    p.sob_encomenda = True
    db.session.commit()
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    oferta = next(n['offers'] for n in _grafo(corpo) if n.get('name') == 'Tender')
    assert oferta['price'] == '42.50' and oferta['priceCurrency'] == 'BRL'
    assert oferta['availability'].endswith('PreOrder')
    assert 'R$ 42,50' in corpo


def test_dominio_proprio_serve_a_berga_e_kits_redireciona(client, session):
    semear(no_ar=True)
    resp = client.get('/', headers={'Host': DOMINIO})
    assert resp.status_code == 200 and 'Dona Berga' in resp.get_data(as_text=True)
    kits = client.get('/kits/index.html', headers={'Host': DOMINIO})
    assert kits.status_code == 301 and kits.headers['Location'].endswith('/#produtos')


def test_kits_em_dominio_de_bar_ou_produto_e_404(client, session):
    assert client.get('/kits').status_code == 404
    assert client.get('/kits/index.html', headers={'Host': 'feiradebarao.com.br'}).status_code == 404


def test_bar_nao_carrega_produtos(client, session):
    r = Restaurante(nome='Bar X', cnpj='66666666000166', slug='bar-x', subscription_tier='site')
    session.add(r)
    session.commit()
    session.add(ProdutoSite(restaurant_id=r.id, nome='Peça solta'))
    session.commit()
    assert 'Peça solta' not in client.get('/bar/bar-x').get_data(as_text=True)


def test_toda_imagem_do_seed_existe_em_disco():
    import os
    from app.scripts.seed_berga import GALERIA, IMAGENS, SITE
    base = os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'static')
    caminhos = [SITE['hero_foto']] + [f'img/berga/{v}.jpg' for v in IMAGENS.values()] \
        + [f'img/berga/{a}.jpg' for a, _ in GALERIA]
    faltando = [c for c in caminhos if not os.path.isfile(os.path.join(base, c))]
    assert not faltando, faltando
    assert set(IMAGENS) <= {p[0] for p in PRODUTOS}   # nenhuma foto órfã de produto


def test_site_mostra_fotos_e_galeria(client, session):
    semear(no_ar=True)
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    assert 'img/berga/hero.jpg' in corpo and 'img/berga/tender.jpg' in corpo
    assert 'A barraca na Feira de Barão' in corpo


def test_logo_vai_no_menu_no_icone_e_como_imagem_de_compartilhamento(client, session):
    from app.models.modelo_siteconfig import SiteConfig
    semear(no_ar=True)
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    assert 'img/berga/logo.jpg' in corpo
    assert 'rel="icon" type="image/jpeg"' in corpo
    # sem foto de capa, o card de compartilhamento cai na logo
    rest = Restaurante.query.filter_by(slug=SLUG).first()
    SiteConfig.query.filter_by(restaurant_id=rest.id).first().hero_foto = None
    db.session.commit()
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    assert re.search(r'og:image" content="https?://[^"]+img/berga/logo\.jpg', corpo)


def test_produto_sem_foto_fica_fora_da_vitrine_e_do_schema(client, session):
    rest, _ = semear(no_ar=True)
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    sem_foto = [n for n, *_ in PRODUTOS if n not in IMAGENS]
    assert sem_foto                                    # o seed tem produtos sem foto
    for nome in sem_foto:
        assert nome not in corpo, nome
    assert all(n.get('name') not in sem_foto for n in _grafo(corpo))
    # continua no banco/painel e aparece quando ganhar foto
    p = ProdutoSite.query.filter_by(restaurant_id=rest.id, nome='Pastrami de Cupim').first()
    assert p is not None
    p.imagem = 'img/berga/bacon.jpg'
    db.session.commit()
    assert 'Pastrami de Cupim' in client.get(f'/bar/{SLUG}').get_data(as_text=True)


def test_categoria_sem_nenhum_produto_com_foto_some(client, session):
    rest, _ = semear(no_ar=True)
    ProdutoSite.query.filter_by(restaurant_id=rest.id, categoria='Kits').update({'imagem': None})
    db.session.commit()
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    assert '>Kits</button>' not in corpo and '>Defumados</button>' in corpo


def test_kits_responde_no_dominio_do_artesao_mesmo_com_dominios_separados(client, session, monkeypatch):
    """Em produção SEPARAR_DOMINIOS=1: rota fora da lista do tenant vira 302 pro
    domínio do produto. /kits tem que ficar na lista."""
    monkeypatch.setenv('SEPARAR_DOMINIOS', '1')
    semear(no_ar=True)
    resp = client.get('/kits/index.html', headers={'Host': DOMINIO})
    assert resp.status_code == 301 and resp.headers['Location'].endswith('/#produtos')


def test_sem_nenhum_produto_com_foto_mostra_estado_vazio_com_whatsapp(client, session):
    rest, _ = semear(no_ar=True)
    ProdutoSite.query.filter_by(restaurant_id=rest.id).update({'imagem': None})
    db.session.commit()
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    assert 'Catálogo em montagem' in corpo
    assert 'class="tile' not in corpo and 'class="chip"' not in corpo
    assert 'wa.me/5519991563362' in corpo


def test_acessibilidade_basica_da_vitrine(client, session):
    semear(no_ar=True)
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    assert 'class="skip" href="#conteudo"' in corpo and 'id="conteudo"' in corpo
    assert corpo.count('<h1') == 1
    assert 'aria-pressed="true"' in corpo and 'role="group"' in corpo
    assert 'prefers-reduced-motion' in corpo
    assert 'class="cta-bar"' in corpo           # barra de WhatsApp do celular
    assert 'id="produtos"' in corpo             # âncora usada pelo redirect de /kits
