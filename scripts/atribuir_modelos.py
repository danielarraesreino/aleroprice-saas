"""Dá a cada bar o modelo que combina com ele.

O problema que isto resolve
---------------------------
Os 6 modelos existem, são de verdade diferentes (nenhuma fonte em comum entre
dois deles, ordens de seção distintas) e ninguém os via: **os 80 leads estavam
sem `modelo`**, e sem valor o site cai no `classico`. Abrir três prévias
seguidas mostrava três vezes a mesma página. A diferença só aparecia com
`?modelo=` na URL — que só o vendedor usa.

Um catálogo de seis peças que entrega sempre a mesma não é um catálogo.

Como decide
-----------
Pelo que o próprio lead diz. `descritor` e `subline` são as frases que o bar usa
pra se apresentar, e `vibe` é o tom já escolhido. Espeto e churrasco vão pra
`brasa`; casa com palco vai pra `noturno`; cervejaria e chope vão pra `craft`;
casa antiga com história vai pra `tradicional`; cozinha assinada vai pra
`autoral`. O que não se encaixa fica no `classico`, que é o completo — e é a
resposta certa pra bar que faz um pouco de tudo.

A ordem das regras importa: a primeira que casa ganha. Um bar de espeto COM
palco é uma espetaria com música, não uma casa de show — quem manda é o que sai
da cozinha.

    python3 scripts/atribuir_modelos.py          # mostra o que faria
    python3 scripts/atribuir_modelos.py --gravar
"""
import argparse
import glob
import os
import re
import sys
import unicodedata

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_LEADS = os.path.join(REPO, 'app', 'data', 'leads')

# (modelo, palavras que o entregam). Primeira regra que casa ganha.
REGRAS = (
    ('brasa',       ('espeto', 'espetinho', 'espetaria', 'churrasc', 'brasa',
                     'costela', 'picanha', 'parrilla', 'grelha')),
    ('craft',       ('cervejaria', 'chopp', 'chope', 'artesanal', 'brewpub',
                     'taproom', 'microcervejaria', 'ipa', 'pub')),
    ('noturno',     ('música ao vivo', 'musica ao vivo', 'ao vivo', 'palco',
                     'show', 'balada', 'drinks', 'blues', 'samba', 'sertanejo')),
    ('tradicional', ('desde 19', 'desde 20', 'tradicional', 'antigo', 'história',
                     'historia', 'família', 'familia', 'gerações', 'geracoes',
                     'raiz', 'clássic')),
    ('autoral',     ('autoral', 'chef', 'bistrô', 'bistro', 'gastronomia',
                     'contemporân', 'assinatura', 'degustação', 'wine', 'vinho')),
)

# Quando o texto não entrega nada, a vibe já escolhida vale como pista.
POR_VIBE = {'pub': 'craft', 'hamburgueria': 'noturno', 'praia': 'autoral'}


def _norm(texto):
    t = unicodedata.normalize('NFD', (texto or '').lower())
    return ''.join(c for c in t if unicodedata.category(c) != 'Mn')


# Bar-vitrine tem modelo FIXO: ele existe pra demonstrar aquele modelo. Sem
# esta exceção a heurística os reclassifica pelo texto — o Fogo & Sal, que é a
# vitrine do `autoral`, virava `brasa` porque a descrição fala de fogo, e a
# Sala Vermelha (vitrine do `noturno`) virava `brasa` por causa da costela.
# Aí a página que existe pra mostrar um modelo mostra outro.
VITRINE_FIXA = {
    'bar-do-ze': 'classico',
    'vitrine-tap-cinco': 'craft',
    'vitrine-armazem-1948': 'tradicional',
    'vitrine-fogo-e-sal': 'autoral',
    'vitrine-sala-vermelha': 'noturno',
    'vitrine-brasa-velha': 'brasa',
}


def escolher(lead, slug=None):
    """Devolve (modelo, motivo). Motivo é o que casou — some no relatório."""
    if slug in VITRINE_FIXA:
        return VITRINE_FIXA[slug], 'vitrine deste modelo'
    site = lead.get('site') or {}
    texto = _norm(' '.join(str(site.get(c) or '') for c in
                           ('descritor', 'subline', 'tagline', 'kicker')))
    pratos = _norm(' '.join(str(i.get('nome') or '')
                            for i in (lead.get('cardapio') or [])))
    tudo = f'{texto} {pratos}'

    for modelo, palavras in REGRAS:
        for p in palavras:
            if _norm(p) in tudo:
                return modelo, f'"{p}"'

    vibe = (site.get('vibe') or '').strip()
    if vibe in POR_VIBE:
        return POR_VIBE[vibe], f'vibe {vibe}'
    return 'classico', 'sem pista — o completo'


def gravar(caminho, modelo):
    texto = open(caminho, encoding='utf-8').read()
    if re.search(r'^\s+modelo:', texto, re.M):
        return False
    linha = f'  modelo: {modelo}'
    novo = re.sub(r'^(site:\n)', rf'\1{linha}\n', texto, count=1, flags=re.M)
    if novo == texto:
        return False
    open(caminho, 'w', encoding='utf-8').write(novo)
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--gravar', action='store_true')
    a = p.parse_args()

    contagem, gravados = {}, 0
    print(f'{"bar":26} {"modelo":13} porque')
    print('-' * 74)
    for caminho in sorted(glob.glob(os.path.join(DIR_LEADS, '*.yml'))):
        bruto = open(caminho, encoding='utf-8').read()
        if 'NÃO VISITAR' in bruto:
            continue
        lead = yaml.safe_load(bruto) or {}
        slug = os.path.basename(caminho)[:-4]
        modelo, motivo = escolher(lead, slug)
        contagem[modelo] = contagem.get(modelo, 0) + 1
        marca = ''
        if a.gravar and gravar(caminho, modelo):
            gravados += 1
            marca = ' ✓'
        print(f'{slug[:26]:26} {modelo:13} {motivo}{marca}')

    print(f'\n{"":26} distribuição:')
    for m, n in sorted(contagem.items(), key=lambda x: -x[1]):
        print(f'{"":26} {m:13} {n:3} {"█" * n}')
    if a.gravar:
        print(f'\n{gravados} leads gravados. Rode `flask --app app aplicar-demos`.')
    else:
        print('\nModo leitura. Use --gravar pra escrever nos leads.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
