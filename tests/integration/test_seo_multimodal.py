"""Imagens para busca e IA multimodal: llms.txt, sitemap de imagens e títulos."""
import re

from app.utils import memoria as mem


def _verbete_com_foto():
    return next(v for v in mem.verbetes() if mem.foto_url(v.get('foto')))


def test_llms_traz_fotos_da_memoria_com_legenda_e_credito(client, session):
    v = _verbete_com_foto()
    foto = mem.foto_url(v['foto'])
    resumo = client.get('/llms.txt').get_data(as_text=True)
    completo = client.get('/llms-full.txt').get_data(as_text=True)
    assert '](https://' in resumo and 'og-feira.jpg)' in resumo
    assert foto in completo and v['foto']['credito'] in completo


def test_sitemap_tem_foto_do_verbete(client, session):
    v = _verbete_com_foto()
    xml = client.get('/sitemap.xml').get_data(as_text=True)
    bloco = re.search(rf"<loc>[^<]*/memoria/{v['slug']}</loc>(.*?)</url>", xml, re.S).group(1)
    assert mem.foto_url(v['foto']) in bloco and '<image:loc>https://' in bloco


def test_home_com_titulo_e_descricao_no_tamanho_do_google(client, session):
    html = client.get('/').get_data(as_text=True)
    titulo = re.search(r'<title>(.*?)</title>', html).group(1)
    descricao = re.search(r'name="description" content="([^"]*)"', html).group(1)
    assert len(titulo) <= 60 and len(descricao) <= 155


def test_arquivo_chave_do_indexnow(client, session):
    from app.routes.publico.views import INDEXNOW_CHAVE
    r = client.get(f'/{INDEXNOW_CHAVE}.txt')
    assert r.status_code == 200 and r.get_data(as_text=True) == INDEXNOW_CHAVE


def test_feira_tem_faq_visivel_e_faqpage_so_na_geral(client, session):
    import json
    html = client.get('/feira').get_data(as_text=True)
    assert 'id="faq-titulo"' in html and 'A entrada na Feira de Barão é paga?' in html
    ld = [json.loads(x) for x in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    faq = next(d for d in ld if d.get('@type') == 'FAQPage')
    assert len(faq['mainEntity']) >= 5
    assert 'FAQPage' not in client.get('/feira?q=geleia').get_data(as_text=True)
