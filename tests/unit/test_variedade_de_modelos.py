"""A campanha não pode servir a mesma página pra todo bar.

Existiam seis modelos, de verdade diferentes — nenhuma fonte em comum entre dois
deles, ordens de seção distintas. E mesmo assim quem abria três prévias seguidas
via três vezes a mesma página, porque **nenhum dos 80 leads definia `modelo`** e
sem valor o site cai no `classico`. Os outros cinco só apareciam com `?modelo=`
na URL, que só o vendedor usa.

Um catálogo que entrega sempre a mesma peça não é catálogo. Estes testes
prendem as duas metades do estrago: os leads têm que distribuir, e os modelos
têm que continuar sendo diferentes entre si.
"""
import glob
import os
import re

import pytest
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR_LEADS = os.path.join(REPO, 'app', 'data', 'leads')
DIR_MODELOS = os.path.join(REPO, 'app', 'templates', 'site')


def _leads():
    for caminho in sorted(glob.glob(os.path.join(DIR_LEADS, '*.yml'))):
        bruto = open(caminho, encoding='utf-8').read()
        if 'NÃO VISITAR' in bruto:
            continue
        yield os.path.basename(caminho)[:-4], (yaml.safe_load(bruto) or {})


def _modelo(lead):
    return ((lead.get('site') or {}).get('modelo') or '').strip()


def test_todo_lead_declara_seu_modelo():
    """Sem `modelo` no YAML o bar cai no clássico — foi assim que os 80 caíram."""
    sem = [slug for slug, lead in _leads() if not _modelo(lead)]

    assert not sem, (
        f'{len(sem)} leads sem `site.modelo` — vão todos renderizar o clássico: '
        f'{", ".join(sem[:8])}')


def test_a_campanha_usa_os_seis_modelos():
    """Não basta ter modelo: os seis têm que estar em uso.

    Se cinco bares usam `craft` e ninguém usa `brasa`, o vendedor não tem o que
    mostrar quando o bar é uma espetaria.
    """
    from app.utils.modelos import opcoes_de_modelo

    usados = {_modelo(lead) for _, lead in _leads()}
    todos = {o['valor'] for o in opcoes_de_modelo()}

    assert todos <= usados, f'modelos sem nenhum bar: {sorted(todos - usados)}'


def test_nenhum_modelo_domina_a_campanha():
    """Metade da campanha num modelo só é o mesmo problema, mais devagar."""
    from collections import Counter

    contagem = Counter(_modelo(lead) for _, lead in _leads())
    total = sum(contagem.values())
    maior, n = contagem.most_common(1)[0]

    assert n <= total * 0.45, (
        f'{maior} tem {n} de {total} bares ({n / total:.0%}) — a campanha volta '
        'a parecer um modelo só')


def test_os_modelos_nao_compartilham_tipografia():
    """A diferença tem que estar no template, não só no nome.

    Fonte é o que se nota primeiro. Dois modelos com a mesma família são duas
    variações da mesma página — que foi a leitura de quem olhou e disse que era
    tudo igual.
    """
    # O caminho de cada modelo sai do próprio registro — o `classico` é a
    # landing original (`site/landing.html`) e só os outros cinco vivem em
    # `site/modelos/`. Varrer o diretório encontrava cinco e deixava o clássico,
    # justamente o que todo mundo estava vendo, fora da comparação.
    from app.utils.modelos import MODELOS

    fontes = {}
    for nome, m in MODELOS.items():
        caminho = os.path.join(REPO, 'app', 'templates', m['arquivo'])
        texto = open(caminho, encoding='utf-8').read()
        fontes[nome] = set(re.findall(r'family=([A-Za-z+]+)', texto))

    assert len(fontes) >= 6, f'só {len(fontes)} modelos com tipografia própria'
    vazios = [n for n, f in fontes.items() if not f]
    assert not vazios, f'modelos sem fonte própria: {vazios}'

    nomes = sorted(fontes)
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            comum = fontes[a] & fontes[b]
            assert not comum, f'{a} e {b} dividem tipografia: {sorted(comum)}'


@pytest.mark.parametrize('slug,esperado', [
    ('bar-do-ze', 'classico'),
    ('vitrine-tap-cinco', 'craft'),
    ('vitrine-armazem-1948', 'tradicional'),
    ('vitrine-fogo-e-sal', 'autoral'),
    ('vitrine-sala-vermelha', 'noturno'),
    ('vitrine-brasa-velha', 'brasa'),
])
def test_cada_vitrine_mostra_o_modelo_que_promete(slug, esperado):
    """Bar-vitrine existe pra demonstrar um modelo específico.

    A heurística que atribuiu os 80 lia o texto do lead, e o texto trai: o Fogo
    & Sal (vitrine do `autoral`) virava `brasa` porque a descrição fala de fogo,
    e a Sala Vermelha (vitrine do `noturno`) virava `brasa` por causa da
    costela. A página que existe pra mostrar um modelo mostrava outro.
    """
    caminho = os.path.join(DIR_LEADS, f'{slug}.yml')
    lead = yaml.safe_load(open(caminho, encoding='utf-8').read()) or {}

    assert _modelo(lead) == esperado
