"""Capa viva (loop do topo do site) e card do almoço do dia, mundo tradicional.

    python videos/tradicional/capa_e_card.py capa videos/tradicional/roteiros/emporio-do-nono.json
    python videos/tradicional/capa_e_card.py card videos/tradicional/roteiros/emporio-do-nono.json

Saída em videos/tradicional/saida/<slug>-capa/ e <slug>-card/ (projetos HyperFrames).
Mesmo desenho de gerar.py: papel, retrato emoldurado, Playfair; conteúdo vem do roteiro.
"""
import json
import os
import shutil
import sys

from PIL import Image

from gerar import AQUI, STATIC, DIA, e, palavras

GRAO = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='320' height='320'>"
        "<filter id='g'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' seed='7'/>"
        "<feColorMatrix values='0 0 0 0 .35 0 0 0 0 .25 0 0 0 0 .15 0 0 0 .9 0'/></filter>"
        "<rect width='100%' height='100%' filter='url(%23g)'/></svg>")


def _projeto(nome, w, h, dur, cenas, titulo):
    saida = os.path.join(AQUI, 'saida', nome)
    os.makedirs(os.path.join(saida, 'compositions'), exist_ok=True)
    os.makedirs(os.path.join(saida, 'assets'), exist_ok=True)
    hosts = '\n'.join(
        f'      <div id="{cid}" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" '
        f'data-start="0" data-duration="{dur}" data-track-index="{i}" data-track-kind="graphics" '
        f'data-width="{w}" data-height="{h}" style="z-index:{i + 1}"></div>' for i, (cid, _) in enumerate(cenas))
    for cid, corpo in cenas:
        open(os.path.join(saida, 'compositions', f'{cid}.html'), 'w', encoding='utf-8').write(corpo)
    open(os.path.join(saida, 'index.html'), 'w', encoding='utf-8').write(f'''<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={w}, height={h}" />
    <title>{e(titulo)}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>* {{ margin:0; padding:0; box-sizing:border-box; }} html, body {{ width:{w}px; height:{h}px; overflow:hidden; background:{DIA['chao']}; }}</style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="{w}" data-height="{h}">
{hosts}
    </div>
    <script>window.__timelines = window.__timelines || {{}}; window.__timelines["main"] = gsap.timeline({{ paused: true }});</script>
  </body>
</html>
''')
    for arq in ('hyperframes.json', 'package.json'):
        shutil.copy(os.path.join(AQUI, 'venda-vertical', arq), os.path.join(saida, arq))
    json.dump({'id': nome, 'name': titulo}, open(os.path.join(saida, 'meta.json'), 'w'), ensure_ascii=False)
    return saida


def _copia(saida, src):
    orig = os.path.join(STATIC, src)
    shutil.copy(orig, os.path.join(saida, 'assets', os.path.basename(src)))
    return os.path.basename(src), Image.open(orig).size


def capa(d):
    """Loop de 8 s, 900x600, mudo. Três fotos, cada uma com um empurrão lento; a última
    troca volta exatamente ao quadro 0, então o loop não tem emenda visível."""
    W, H, DUR = 900, 600, 8.0
    fotos = d['capa_fotos']
    nome = f"{d['slug']}-capa"
    saida = os.path.join(AQUI, 'saida', nome)
    os.makedirs(os.path.join(saida, 'assets'), exist_ok=True)
    arqs = []
    for src in fotos:
        arq, (fw, fh) = _copia(saida, src)
        # escala máxima do empurrão (1.06) vezes o quadro não pode passar do original
        assert fw >= W * 1.06 and fh >= H * 1.06, f'{src} pequena demais para a capa ({fw}x{fh})'
        arqs.append(arq)
    imgs = '\n'.join(
        f'      <div class="cv-f" id="cv-f{i}"><img src="assets/{a}" width="{W}" height="{H}" alt=""></div>'
        for i, a in enumerate(arqs))
    corpo = f'''<template>
  <style>
    #capa-root{{position:absolute;inset:0;overflow:hidden;background:{DIA['chao']}}}
    #capa-root .cv-f{{position:absolute;inset:0;opacity:0}}
    #capa-root .cv-f img{{display:block;width:{W}px;height:{H}px;object-fit:cover}}
    #cv-f0{{opacity:1}}
  </style>
  <div id="capa-root" data-composition-id="capa" data-width="{W}" data-height="{H}">
    <div id="cv-clip" class="clip" data-start="0" data-duration="{DUR}" data-track-index="1" data-layout-ignore>
{imgs}
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{paused:true}});
    // cada foto: 2,7 s de empurrão; troca em "blur swap" de 0,2 s sobre o mesmo palco
    tl.fromTo("#cv-f0 img", {{scale:1}}, {{scale:1.06, duration:2.8, ease:"none"}}, 0);
    tl.to("#cv-f0", {{opacity:0, filter:"blur(8px)", duration:.2, ease:"power2.in"}}, 2.6);
    tl.fromTo("#cv-f1", {{opacity:0, filter:"blur(8px)"}}, {{opacity:1, filter:"blur(0px)", duration:.2, ease:"power2.out"}}, 2.6);
    tl.fromTo("#cv-f1 img", {{scale:1.06, x:-12}}, {{scale:1, x:12, duration:2.9, ease:"none"}}, 2.6);
    tl.to("#cv-f1", {{opacity:0, filter:"blur(8px)", duration:.2, ease:"power2.in"}}, 5.3);
    tl.fromTo("#cv-f2", {{opacity:0, filter:"blur(8px)"}}, {{opacity:1, filter:"blur(0px)", duration:.2, ease:"power2.out"}}, 5.3);
    tl.fromTo("#cv-f2 img", {{scale:1}}, {{scale:1.05, duration:2.7, ease:"none"}}, 5.3);
    // volta ao quadro 0 (foto 0, escala 1) antes do fim: o loop fecha sem salto
    tl.to("#cv-f2", {{opacity:0, filter:"blur(8px)", duration:.2, ease:"power2.in"}}, 7.75);
    tl.fromTo("#cv-f0", {{opacity:0, filter:"blur(8px)"}}, {{opacity:1, filter:"blur(0px)", immediateRender:false, duration:.2, ease:"power2.out"}}, 7.75);
    tl.set("#cv-f0 img", {{scale:1}}, 7.75);
    window.__timelines["capa"] = tl;
  </script>
</template>
'''
    return _projeto(nome, W, H, DUR, [('capa', corpo)], f"{d['nome']} — capa viva")


def card(d):
    """Card do almoço do dia, 1080x1920, 8 s: cardápio de mesa em papel, a lista de hoje se
    escreve prato a prato e para."""
    W, H, DUR = 1080, 1920, 8.0
    a = d['almoco']
    nome = f"{d['slug']}-card"
    saida = os.path.join(AQUI, 'saida', nome)
    os.makedirs(os.path.join(saida, 'assets'), exist_ok=True)
    foto, (fw, fh) = _copia(saida, a['foto'])
    logo, _ = _copia(saida, d['logo_src'])
    pw = min(600, fw)
    ph = round(pw * fh / fw)
    topo_tit = 170 + ph + 36 + 64
    topo_lista = topo_tit + 210
    # cada prato ~104 px (nome + detalhe); o rodapé vem sempre depois do último
    topo_pe = topo_lista + 104 * len(a['pratos']) + 48
    def _item(i, p):
        det = '<span>' + e(p['det']) + '</span>' if p.get('det') else ''
        return f'        <li class="ca-i" id="ca-i{i}"><b>{e(p["nome"])}</b>{det}</li>'
    itens = '\n'.join(_item(i, p) for i, p in enumerate(a['pratos']))
    corpo = f'''<template>
  <style>
    #card-root{{position:absolute;inset:0;font-family:"Playfair Display",serif;color:{DIA['tinta']};
      background:{DIA['chao']}}}
    #ca-grao{{position:absolute;inset:0;background-image:url("{GRAO}");opacity:.06;mix-blend-mode:multiply}}
    #ca-foto{{position:absolute;left:{(W - pw) // 2 - 18}px;top:170px;background:#fffaf0;padding:18px 18px 18px;
      box-shadow:0 18px 40px rgba(61,36,21,.30)}}
    #ca-foto img{{display:block;object-fit:cover}}
    #ca-foto::before{{content:"";position:absolute;top:-18px;left:50%;width:120px;height:36px;margin-left:-60px;
      background:rgba(199,166,108,.6);transform:rotate(-3deg)}}
    #ca-tit{{position:absolute;left:96px;top:{topo_tit}px;width:888px}}
    #ca-tit h1{{font-weight:900;font-size:100px;line-height:.95;letter-spacing:-.015em}}
    #ca-tit p{{font-style:italic;font-weight:700;font-size:44px;color:{DIA['madeira']};margin-top:10px}}
    #ca-lista{{position:absolute;left:96px;top:{topo_lista}px;width:888px;list-style:none;
      border-top:3px double rgba(107,69,38,.5)}}
    #ca-lista .ca-i{{padding:12px 0;border-bottom:2px dotted rgba(107,69,38,.35)}}
    #ca-lista .ca-i b{{display:block;font-weight:700;font-size:40px;line-height:1.15}}
    #ca-lista .ca-i span{{display:block;font-size:28px;line-height:1.3;color:#6d5540;margin-top:4px}}
    #ca-pe{{position:absolute;left:96px;right:96px;top:{topo_pe}px;display:flex;align-items:center;gap:24px}}
    #ca-pe img{{width:120px;height:120px;object-fit:contain;background:#fffaf0;padding:8px;
      box-shadow:0 10px 22px rgba(61,36,21,.25)}}
    #ca-pe b{{display:block;font-weight:900;font-size:44px;line-height:1.1}}
    #ca-pe span{{display:block;font-weight:900;font-size:52px;color:{DIA['esmalte']};line-height:1.1}}
  </style>
  <div id="card-root" data-composition-id="card" data-width="{W}" data-height="{H}">
    <div id="ca-grao" data-layout-ignore></div>
    <div id="ca-cf" class="clip" data-start="0" data-duration="{DUR}" data-track-index="1">
      <figure id="ca-foto"><img src="assets/{foto}" width="{pw}" height="{ph}" alt=""></figure>
    </div>
    <div id="ca-ct" class="clip" data-start="0" data-duration="{DUR}" data-track-index="2">
      <div id="ca-tit"><h1 id="ca-h">{e(a['titulo'])}</h1><p id="ca-data">{e(a['data'])}</p></div>
    </div>
    <div id="ca-cl" class="clip" data-start="0" data-duration="{DUR}" data-track-index="3">
      <ul id="ca-lista">
{itens}
      </ul>
    </div>
    <div id="ca-cp" class="clip" data-start="0" data-duration="{DUR}" data-track-index="4" data-layout-allow-caption-zone>
      <div id="ca-pe"><img src="assets/{logo}" width="120" height="120" alt=""><div><b>Peça pelo WhatsApp</b><span>{e(d['whatsapp'])}</span></div></div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{paused:true}});
    tl.fromTo("#ca-foto", {{rotation:-4, scale:1.03}}, {{rotation:-1.5, scale:1, duration:.7, ease:"expo.out"}}, 0);
    tl.fromTo("#ca-h", {{opacity:.3, filter:"blur(6px)"}}, {{opacity:1, filter:"blur(0px)", duration:.2, ease:"power4.out"}}, .25);
    tl.fromTo("#ca-data", {{opacity:0}}, {{opacity:1, duration:.25, ease:"power2.out"}}, .5);
    tl.fromTo("#ca-lista .ca-i", {{opacity:0, x:-28}}, {{opacity:1, x:0, duration:.45, ease:"expo.out", stagger:.32}}, .8);
    tl.fromTo("#ca-pe", {{opacity:0, y:30}}, {{opacity:1, y:0, duration:.5, ease:"expo.out"}}, .9 + .32 * {len(a['pratos'])});
    window.__timelines["card"] = tl;
  </script>
</template>
'''
    return _projeto(nome, W, H, DUR, [('card', corpo)], f"{d['nome']} — almoço do dia")


if __name__ == '__main__':
    peca, roteiro = sys.argv[1], sys.argv[2]
    d = json.load(open(roteiro, encoding='utf-8'))
    print({'capa': capa, 'card': card}[peca](d))
