"""Memória Viva: verbetes em YAML, /memoria, mapa da home e WhatsApp certo."""
from app.utils import memoria as mem


def test_todo_verbete_tem_fonte_slug_unico_e_texto():
    vs = mem.verbetes()
    assert len(vs) >= 20
    assert len({v['slug'] for v in vs}) == len(vs)
    for v in vs:
        assert v.get('fontes'), v['slug']
        assert v.get('resumo') and v.get('texto'), v['slug']
        if v.get('lugar'):
            assert -23.1 < v['lugar']['lat'] < -22.6 and -47.4 < v['lugar']['lng'] < -46.8, v['slug']


def test_seis_capitulos_para_o_mapa_da_home():
    assert [v['capitulo'] for v in mem.capitulos()] == [1, 2, 3, 4, 5, 6]


def test_hub_e_verbete_respondem(client, session):
    html = client.get('/memoria').get_data(as_text=True)
    assert 'Memória Viva' in html and 'historiadebaraogeraldo.wordpress.com' in html
    v = mem.verbetes()[0]
    pagina = client.get(f"/memoria/{v['slug']}").get_data(as_text=True)
    assert v['titulo'] in pagina and '"Article"' in pagina
    assert client.get('/memoria/nao-existe').status_code == 404


def test_verbete_com_lugar_tem_mapa_e_street_view(client, session):
    v = next(v for v in mem.verbetes() if v.get('lugar'))
    html = client.get(f"/memoria/{v['slug']}").get_data(as_text=True)
    assert 'map_action=pano' in html and 'maps/search/?api=1' in html


def test_home_monta_os_cartoes_e_pinos_dos_verbetes(client, session):
    html = client.get('/').get_data(as_text=True)
    for v in mem.capitulos():
        assert v['titulo'] in html
    assert 'map_action=pano' in html and '/memoria/' in html


def test_whatsapp_do_gustavo_nao_aparece_mais(client, session):
    for url in ('/', '/memoria'):
        assert '5519999779942' not in client.get(url).get_data(as_text=True)


def test_sitemap_traz_a_memoria(client, session):
    xml = client.get('/sitemap.xml', headers={'Host': 'feiradebarao.com.br'}).get_data(as_text=True)
    assert '/memoria</loc>' in xml and f"/memoria/{mem.verbetes()[0]['slug']}" in xml
