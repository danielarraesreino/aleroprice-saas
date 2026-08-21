"""Gera as imagens de compartilhamento (og:image) das páginas do produto.

Por que isso importa
--------------------
A venda acontece no WhatsApp: o link vai para o dono do bar e ele decide abrir
ou não pelo que aparece no preview. Nenhuma das páginas tinha `og:image`, então
o link chegava como uma tira de texto cinza — do lado de propostas que chegam
com foto.

O que as imagens NÃO têm
------------------------
Texto. Modelo de imagem escreve palavra torta, e o preview do WhatsApp já
estampa título e descrição por cima — letra gerada ali vira ruído duplicado.
Também não têm rosto reconhecível: são fotos de ambiente, não de pessoas.

Uso:
    export FAL_KEY='...'
    python3 scripts/gerar_og.py            # mostra o que faria
    python3 scripts/gerar_og.py --gravar
"""
import argparse
import json
import os
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(REPO, 'app', 'static', 'img', 'og')

# Formato do preview: 1200x630 é o que WhatsApp, Facebook e LinkedIn recortam
# sem cortar as beiradas. Quadrado ou 16:9 chegam com faixa preta ou cropados.
LARGURA, ALTURA = 1200, 630

# Teto de peso do preview: acima disso o WhatsApp costuma desistir de carregar
# a miniatura, e o link volta a chegar como tira de texto.
TETO_BYTES = 300 * 1024

# Modelo: o `flux/dev` entregava imagem com cara de render — luz uniforme demais,
# bokeh de cinema, composição de banco de imagem. Comparado lado a lado com
# `flux-realism` e com o próprio dev, o `flux-pro/v1.1-ultra` foi o único que
# passa por fotografia de rua. Custa mais por imagem; são três peças.
MODELO = 'fal-ai/flux-pro/v1.1-ultra'

# O que separa foto de render está aqui.
#
# Nada de "cinematic", "beautiful", "stunning": esses termos puxam o modelo
# justamente para o look sintético. O que se pede é o contrário — luz disponível
# de verdade, grão, enquadramento de quem não é fotógrafo. Hora azul em vez de
# noite fechada porque a peça é miniatura de link: precisa ser legível a 400px
# de largura no WhatsApp.
#
# "no text, no signage": modelo de imagem escreve letra torta, e o teste com
# outro modelo devolveu uma fachada com "BAR" e "ANR" escritos errado. O preview
# já estampa título e descrição por cima.
ASSINATURA = (
    'blue hour, available light only, mixed warm tungsten and fluorescent, '
    'visible film grain, handheld, slightly crooked framing, ordinary snapshot, '
    'unremarkable composition, deep focus, brazilian neighborhood, '
    'no text, no signage, no letters, no watermark, no logos, '
    'no recognizable faces, not cinematic, no bokeh'
)

PECAS = {
    # Enquadramento fechado de propósito: na versão anterior a rua abria para
    # fachadas ao fundo, e o modelo encheu as vitrines de letreiro inventado
    # ("CLUERSO"). Letra torta é o que mais denuncia imagem gerada. Sem linha do
    # horizonte com comércio, não há onde escrever.
    'og-feira': (
        'Close view of wooden trestle market stalls with striped canvas awnings, '
        'stacked plastic crates and cardboard boxes, bare bulbs hanging on a '
        'wire, hands of a vendor arranging produce, worn asphalt underfoot, '
        'shallow street behind, no storefronts visible'
    ),
    'og-barao': (
        'A small brazilian corner bar seen from across the street, white plastic '
        'chairs and tables on the sidewalk, a few people sitting with beer '
        'bottles, fluorescent tube light inside, tiled facade, parked motorbike, '
        'power cables overhead, tree branches'
    ),
    'og-coletivo': (
        'An ordinary brazilian city street early in the morning, wet asphalt, '
        'closed metal roller shutters, a bus stop, litter on the curb, '
        'overhead wires, no people, flat overcast light'
    ),
}


def gerar(prompt, chave):
    corpo = json.dumps({
        'prompt': f'{prompt}, {ASSINATURA}',
        'aspect_ratio': '16:9',
        'num_images': 1,
        'enable_safety_checker': True,
        # `raw` é o que desliga o embelezamento do modelo. Sem ele a imagem sai
        # com contraste e saturação de propaganda — exatamente o que faz o
        # resultado gritar "IA".
        'raw': True,
    }).encode()
    req = urllib.request.Request(
        f'https://fal.run/{MODELO}', data=corpo,
        headers={'Authorization': f'Key {chave}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.load(r)['images'][0]['url']


def baixar(url, caminho):
    """Baixa e ajusta ao formato de preview.

    O `flux-pro/v1.1-ultra` devolve 2752x1536 com ~1,5 MB. Guardar isso é
    mandar megabytes para quem vai ver 400px de largura na conversa do
    WhatsApp — e preview pesado é preview que não carrega no 4G, que é
    exatamente onde o dono do bar abre o link.
    """
    req = urllib.request.Request(url, headers={'User-Agent': 'feira-og'})
    with urllib.request.urlopen(req, timeout=120) as r:
        dados = r.read()

    from PIL import Image
    import io
    im = Image.open(io.BytesIO(dados)).convert('RGB')
    im = im.resize((LARGURA, ALTURA), Image.LANCZOS)
    for q in (88, 84, 80, 76, 72, 68):
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=q, optimize=True, progressive=True)
        if buf.tell() <= TETO_BYTES:
            break
    with open(caminho, 'wb') as f:
        f.write(buf.getvalue())
    return buf.tell()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--gravar', action='store_true')
    p.add_argument('--so', help='gera só esta peça (ex.: og-barao)')
    a = p.parse_args()

    chave = os.environ.get('FAL_KEY')
    if a.gravar and not chave:
        print('  FAL_KEY não está no ambiente.', file=sys.stderr)
        return 1

    os.makedirs(DESTINO, exist_ok=True)
    pecas = {a.so: PECAS[a.so]} if a.so else PECAS

    for nome, prompt in pecas.items():
        caminho = os.path.join(DESTINO, f'{nome}.jpg')
        if not a.gravar:
            print(f'  {nome:14} {prompt[:66]}…')
            continue
        url = gerar(prompt, chave)
        kb = baixar(url, caminho) // 1024
        print(f'  {nome:14} {kb:4} KB  {caminho}')

    if not a.gravar:
        print('\n  Modo leitura. Use --gravar (com FAL_KEY no ambiente).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
