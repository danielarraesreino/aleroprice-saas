"""Prévia de ARTESÃO é indexável (decisão do dono: "onde comprar artesanato em
Barão Geraldo" tem de achar os expositores). Prévia de BAR segue noindex."""
import json
import re

from app.extensions import db
from app.models.modelo_restaurante import Restaurante
from app.models.modelo_siteconfig import SiteConfig
from app.scripts.seed_berga import SLUG, semear

PRODUTO = 'feiradebarao.com.br'


def _artesao_previa():
    rest, _ = semear(no_ar=True)
    rest.tipo_conta = 'demo'
    rest.dominio = None
    db.session.commit()
    return rest


def _bar_previa(session):
    r = Restaurante(nome='Tatu Bola', slug='tatu-bola', tipo_conta='demo')
    session.add(r)
    session.commit()
    session.add(SiteConfig(restaurant_id=r.id, nome='Tatu Bola',
                           endereco='Av. Santa Isabel, 57 — Barão Geraldo, Campinas - SP'))
    session.commit()
    return r


def _sitemap(client):
    return client.get('/sitemap.xml', headers={'Host': PRODUTO}).get_data(as_text=True)


def _tem_image(no):
    if isinstance(no, dict):
        return 'image' in no or any(_tem_image(v) for v in no.values())
    if isinstance(no, list):
        return any(_tem_image(v) for v in no)
    return False


def test_artesao_previa_e_indexavel_e_mantem_a_faixa(client, session):
    _artesao_previa()
    corpo = client.get(f'/bar/{SLUG}', headers={'Host': PRODUTO}).get_data(as_text=True)
    assert 'content="index,follow"' in corpo
    assert 'noindex' not in corpo and 'nofollow' not in corpo and 'noarchive' not in corpo
    assert 'faixa-previa' in corpo and 'imagens são ilustrativas' in corpo


def test_artesao_previa_entra_no_sitemap_com_lastmod(client, session):
    rest = _artesao_previa()
    xml = _sitemap(client)
    assert f'<loc>https://{PRODUTO}/bar/{SLUG}</loc>' in xml
    bloco = xml.split(f'/bar/{SLUG}</loc>')[1].split('</url>')[0]
    assert '<lastmod>' in bloco


def test_portal_lista_expo_termos_e_privacidade_no_sitemap(client, session):
    xml = _sitemap(client)
    for caminho in ('/expor', '/termos', '/privacidade'):
        assert f'<loc>https://{PRODUTO}{caminho}</loc>' in xml


def test_bar_previa_segue_noindex_e_fora_do_sitemap(client, session):
    _bar_previa(session)
    corpo = client.get('/bar/tatu-bola', headers={'Host': PRODUTO}).get_data(as_text=True)
    assert 'noindex,nofollow,noarchive' in corpo
    assert 'tatu-bola' not in _sitemap(client)


def test_json_ld_de_previa_nao_tem_image(client, session):
    _artesao_previa()
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    bruto = re.search(r'<script type="application/ld\+json">(.*?)</script>', corpo, re.S).group(1)
    grafo = json.loads(bruto)['@graph']
    assert any(n['@type'] == 'Product' for n in grafo)
    assert not _tem_image(grafo)


def test_json_ld_de_cliente_mantem_image(client, session):
    semear(no_ar=True)      # cliente (Dona Berga) com foto real
    corpo = client.get('/', headers={'Host': 'donaberga.com.br'}).get_data(as_text=True)
    bruto = re.search(r'<script type="application/ld\+json">(.*?)</script>', corpo, re.S).group(1)
    assert _tem_image(json.loads(bruto)['@graph'])


def test_cliente_com_dominio_redireciona_301_de_bar_slug(client, session):
    semear(no_ar=True)
    resp = client.get(f'/bar/{SLUG}', headers={'Host': PRODUTO})
    assert resp.status_code == 301
    assert resp.headers['Location'] == 'https://donaberga.com.br/'


def test_artesao_sem_dominio_nao_redireciona(client, session):
    _artesao_previa()
    assert client.get(f'/bar/{SLUG}', headers={'Host': PRODUTO}).status_code == 200


def test_rodape_de_todo_hotsite_linka_a_feira_sem_nofollow(client, session):
    _artesao_previa()
    corpo = client.get(f'/bar/{SLUG}').get_data(as_text=True)
    link = re.search(r'<a [^>]*href="https://feiradebarao\.com\.br/"[^>]*>Feito com a Feira de Barão</a>', corpo)
    assert link and 'nofollow' not in link.group(0)


def test_feira_linka_o_dominio_proprio_e_nao_a_previa(client, session):
    semear(no_ar=True)
    html = client.get('/feira').get_data(as_text=True)
    assert 'https://donaberga.com.br/' in html
    assert f'/bar/{SLUG}' not in html


def test_llms_full_e_diferente_e_maior_que_llms(client, session):
    _artesao_previa()
    curto = client.get('/llms.txt', headers={'Host': PRODUTO}).get_data(as_text=True)
    cheio = client.get('/llms-full.txt', headers={'Host': PRODUTO}).get_data(as_text=True)
    assert cheio != curto and len(cheio) > len(curto)
    assert '/cadastro' not in curto and '/cadastro' not in cheio
    for texto in (curto, cheio):
        assert 'Dona Berga' in texto and 'por ano' in texto and 'Perguntas frequentes' in texto
    assert 'O que não existe' in cheio and 'Como contratar' in cheio


def test_llms_traz_whatsapp_quando_configurado(client, session, monkeypatch):
    monkeypatch.setenv('FEIRA_WHATSAPP', '5519999990000')
    texto = client.get('/llms.txt', headers={'Host': PRODUTO}).get_data(as_text=True)
    assert 'https://wa.me/5519999990000' in texto


def test_og_das_paginas_do_portal(client, session):
    feira = client.get('/feira').get_data(as_text=True)
    assert '<meta property="og:type" content="website">' in feira
    campinas = client.get('/site-para-bar-em-campinas').get_data(as_text=True)
    titulo = re.search(r'<title>(.*?)</title>', campinas).group(1)
    desc = re.search(r'<meta name="description" content="(.*?)">', campinas).group(1)
    assert f'<meta property="og:title" content="{titulo}">' in campinas
    assert f'<meta property="og:description" content="{desc}">' in campinas
    expor = client.get('/expor').get_data(as_text=True)
    assert 'property="og:url"' in expor and 'name="twitter:card"' in expor
