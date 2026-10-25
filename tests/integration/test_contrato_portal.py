"""Contrato de design das páginas do portal (feiradebarao.com.br).

Complementa `test_contrato_design.py`, que só cobre os modelos de site. Aqui ficam
as regras que a revisão visual pegou depois que os testes já estavam verdes:
página de venda sem prova visual, sem CTA no fim, chapéu em caixa alta em todo
bloco (tell de IA, R11) e imagem sem tamanho (CLS, R6).

`MAX_CHAPEUS` é um teto por página: pode cair, não pode subir.
"""
import re

import pytest

PAGINAS = ['/', '/feira', '/expor', '/vendedor', '/site-para-bar-em-campinas',
           '/privacidade', '/termos']
VENDA = ['/expor', '/site-para-bar-em-campinas']          # precisam provar e chamar
MAX_CHAPEUS = {'/expor': 1}                                # padrão novo: estrito
TETO_ATUAL = 12                                            # demais páginas: não piorar
CHAPEU = re.compile(r'class="[^"]*\b(?:eyebrow|chapeu-dossie)\b')


@pytest.fixture
def zap(monkeypatch):
    monkeypatch.setenv('FEIRA_WHATSAPP', '5519999990000')


def _html(client, rota):
    r = client.get(rota)
    assert r.status_code == 200, rota
    return r.get_data(as_text=True)


@pytest.mark.parametrize('rota', PAGINAS)
def test_piso_de_toda_pagina_do_portal(client, session, zap, rota):
    h = _html(client, rota)
    assert h.count('<h1') == 1
    assert re.search(r'<title>[^<]{10,}</title>', h)
    assert 'rel="canonical"' in h or 'noindex' in h
    for tag in re.findall(r'<img\b[^>]*>', h):
        assert 'alt=' in tag, tag[:90]
        assert ('width=' in tag and 'height=' in tag) or 'aspect-ratio' in tag, tag[:90]


@pytest.mark.parametrize('rota', PAGINAS)
def test_chapeu_em_caixa_alta_nao_vira_molde(client, session, zap, rota):
    n = len(CHAPEU.findall(_html(client, rota)))
    assert n <= MAX_CHAPEUS.get(rota, TETO_ATUAL), f'{rota}: {n} chapéus'


@pytest.mark.parametrize('rota', [
    '/expor',
    pytest.param('/site-para-bar-em-campinas', marks=pytest.mark.xfail(
        strict=True, reason='dívida: página dos bares ainda sem captura de site real')),
])
def test_pagina_de_venda_prova_e_chama(client, session, zap, rota):
    h = _html(client, rota)
    corpo = h[h.index('<main'):h.index('</main>')] if '<main' in h else h
    assert len(re.findall(r'<img\b', corpo)) >= 1, 'sem prova visual (captura de site real)'
    assert h.count('wa.me/') >= 2, 'faltou CTA: topo e fim da página'
    ultimo = corpo[corpo.rindex('<section'):]
    assert 'wa.me/' in ultimo, 'a última seção precisa terminar em chamada'
