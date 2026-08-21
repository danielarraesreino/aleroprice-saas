"""Deixa toda imagem da campanha abaixo de um teto de peso.

Por que existe
--------------
As capas são vistas em pé na porta do bar, no 4G do celular do vendedor, com o
dono olhando por cima do ombro. Uma capa de 571 KB leva alguns segundos nesse
cenário — e são segundos em que a tela está branca e a pessoa já formou opinião
sobre o produto. O teto de 250 KB é o que cabe nessa conversa.

Como decide
-----------
Reduz o lado maior até `--lado` e vai baixando a qualidade JPEG até caber no
teto, parando na primeira que couber. Não desce abaixo de `--q-min`: capa
borrada é pior que capa lenta, porque a foto é o argumento de venda.

Só grava se o resultado for menor que o original. Quem já está abaixo do teto
não é tocado — reprocessar JPEG degrada a cada passada, e rodar o script duas
vezes não pode piorar o que já estava bom.

    python3 scripts/enxugar_imagens.py            # mostra o que faria
    python3 scripts/enxugar_imagens.py --gravar
"""
import argparse
import glob
import os
import sys

from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_IMG = os.path.join(REPO, 'app', 'static', 'img', 'demo')


def enxugar(caminho, teto, lado_max, q_min, gravar):
    """Devolve (kb_antes, kb_depois, qualidade) ou None se nada a fazer."""
    antes = os.path.getsize(caminho)
    if antes <= teto:
        return None

    import io
    original = Image.open(caminho).convert('RGB')  # JPEG não tem canal alfa

    # Cede qualidade primeiro, resolução só depois: numa foto de bar, textura
    # de grão passa despercebida e falta de pixel não. Três capas não cabiam no
    # teto nem na qualidade mínima — para essas, o lado tem que ceder também.
    melhor = None
    for lado in (lado_max, int(lado_max * 0.85), int(lado_max * 0.72)):
        im = original
        if max(im.size) > lado:
            escala = lado / max(im.size)
            im = im.resize((round(im.width * escala), round(im.height * escala)),
                           Image.LANCZOS)
        for q in (86, 82, 78, 74, 70, 66, 62):
            if q < q_min:
                break
            buf = io.BytesIO()
            # `optimize` recalcula as tabelas de Huffman; `progressive` faz a
            # foto aparecer inteira e ir ficando nítida, em vez de descer por
            # faixas — em rede lenta é a diferença entre "carregando" e
            # "quebrado".
            im.save(buf, 'JPEG', quality=q, optimize=True, progressive=True)
            if melhor is None or buf.tell() < melhor[0]:
                melhor = (buf.tell(), buf.getvalue(), q, max(im.size))
            if buf.tell() <= teto:
                break
        if melhor and melhor[0] <= teto:
            break

    if melhor is None or melhor[0] >= antes:
        return None
    if gravar:
        with open(caminho, 'wb') as f:
            f.write(melhor[1])
    return antes // 1024, melhor[0] // 1024, melhor[2], melhor[3]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--teto-kb', type=int, default=250)
    p.add_argument('--lado', type=int, default=1600)
    p.add_argument('--q-min', type=int, default=62)
    p.add_argument('--gravar', action='store_true')
    a = p.parse_args()

    teto = a.teto_kb * 1024
    poupado = 0
    tocadas = 0
    for caminho in sorted(glob.glob(os.path.join(DIR_IMG, '**', '*.jpg'),
                                    recursive=True)):
        r = enxugar(caminho, teto, a.lado, a.q_min, a.gravar)
        if not r:
            continue
        antes, depois, q, lado = r
        tocadas += 1
        poupado += antes - depois          # já em KB — não dividir de novo
        rel = os.path.relpath(caminho, DIR_IMG)
        alerta = '  ← ainda acima do teto' if depois > a.teto_kb else ''
        print(f'  {rel:44} {antes:4} KB → {depois:3} KB  (q{q}, {lado}px){alerta}')

    print(f'\n  {tocadas} imagens, {poupado / 1024:.1f} MB a menos'
          + ('' if a.gravar else '  [simulação — use --gravar]'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
