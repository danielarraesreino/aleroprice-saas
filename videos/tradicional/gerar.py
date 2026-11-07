"""Monta o vídeo de venda vertical "Um dia na esquina" (mundo tradicional) para uma casa.

    python videos/tradicional/gerar.py videos/tradicional/roteiros/emporio-do-nono.json

Lê o roteiro da casa (horas, linhas, fotos, contato) e escreve um projeto HyperFrames
completo em videos/tradicional/saida/<slug>/ — index.html, uma cena por arquivo em
compositions/ e as fotos em assets/. O desenho (cores, relógio, retratos, movimento) é
do modelo; o conteúdo é da casa. Ver SPEC.md em venda-vertical/.
"""
import html
import json
import os
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
STATIC = os.path.join(RAIZ, 'app', 'static')

W, H, FPS = 1080, 1920, 30

# Paleta do modelo tradicional (app/templates/site/modelos/tradicional.html).
DIA = dict(chao='#f6eddd', tinta='#2d1e13', madeira='#6b4526', esmalte='#b32a1e')
TARDE = dict(chao='#ecd9b6', tinta='#2d1e13', madeira='#6b4526', esmalte='#b32a1e')
NOITE = dict(chao='#22160d', tinta='#f3e6cf', madeira='#c99a63', esmalte='#e85b49')

# Janelas das cenas no filme (s). As cenas se sobrepõem 0,2 s na troca.
JANELAS = [(0.0, 3.8), (3.6, 4.0), (7.4, 4.0)]
FECHO = (11.2, 3.8)
TOTAL = 15.0

e = html.escape


def letras(texto, prefixo):
    return ''.join(f'<span class="{prefixo}-l">{e(c) if c != " " else "&nbsp;"}</span>' for c in texto)


def palavras(texto, prefixo):
    return ' '.join(f'<span class="{prefixo}-p">{e(p)}</span>' for p in texto.split())


def retrato_css(cid):
    return f'''
    #{cid}-root .ret{{position:absolute;background:#fffaf0;padding:18px 18px 64px;
      box-shadow:0 18px 40px rgba(61,36,21,.30);transform-origin:50% 40%}}
    #{cid}-root .ret img{{display:block;object-fit:cover}}
    #{cid}-root .ret figcaption{{position:absolute;left:18px;right:18px;bottom:14px;
      font:italic 700 30px/1.2 "Playfair Display",serif;color:#43290f;text-align:center;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
    #{cid}-root .ret::before{{content:"";position:absolute;top:-18px;left:50%;width:120px;height:36px;
      margin-left:-60px;background:rgba(199,166,108,.6);transform:rotate(-3deg)}}'''


def cena_hora(cid, idx, c, pal, primeira):
    """Uma hora do dia: hora + linha + 3 retratos (A grande, B e C pequenos)."""
    a, b, cc = c['fotos']
    dur = JANELAS[idx][1]
    # Tamanho do retrato = foto no tamanho original, no máximo 640 px de largura.
    def caixa(f, maxw):
        w = min(maxw, f['w'])
        return w, round(w * f['h'] / f['w'])
    aw, ah = caixa(a, 640)
    bw, bh = caixa(b, 400)
    cw, ch = caixa(cc, 400)
    entrada_a = '' if primeira else f'''
    tl.fromTo("#{cid}-a", {{y:160, rotation:-8, opacity:0}}, {{y:0, rotation:-2.5, opacity:1, duration:.55, ease:"expo.out"}}, .3);'''
    assenta_a = f'''
    tl.fromTo("#{cid}-a", {{rotation:-4, scale:1.02}}, {{rotation:-2.5, scale:1, duration:.6, ease:"expo.out"}}, 0);''' if primeira else ''
    hora_in = '' if primeira else f'''
    tl.fromTo("#{cid}-hora .{cid}-l", {{opacity:0, filter:"blur(4px)"}}, {{opacity:1, filter:"blur(0px)", duration:.18, ease:"power4.out", stagger:.06}}, .65);
    tl.fromTo("#{cid}-linha .{cid}-p", {{opacity:0, filter:"blur(6px)"}}, {{opacity:1, filter:"blur(0px)", duration:.13, ease:"power4.out", stagger:.08}}, .95);'''
    return f'''<template>
  <style>
    #{cid}-root{{position:absolute;inset:0;font-family:"Playfair Display",serif;color:{pal['tinta']}}}
    #{cid}-hora{{position:absolute;left:96px;top:610px;font-weight:900;font-size:168px;line-height:1;
      letter-spacing:-.02em;color:{pal['esmalte']};white-space:nowrap}}
    #{cid}-linha{{position:absolute;left:96px;top:800px;width:888px;font-weight:700;font-size:60px;line-height:1.12}}
    {retrato_css(cid)}
  </style>
  <div id="{cid}-root" data-composition-id="{cid}" data-width="{W}" data-height="{H}">
    <div id="{cid}-hora" class="clip" data-start="0" data-duration="{dur}" data-track-index="1">{letras(c['hora'], cid)}</div>
    <div id="{cid}-linha" class="clip" data-start="0" data-duration="{dur}" data-track-index="2">{palavras(c['linha'], cid)}</div>
    <div id="{cid}-pa" class="clip" data-start="0" data-duration="{dur}" data-track-index="3" data-layout-allow-overlap>
      <figure id="{cid}-a" class="ret" style="left:{540 - aw // 2 - 70}px;top:1010px">
        <img src="assets/{a['arq']}" width="{aw}" height="{ah}" alt="">
        <figcaption>{e(a['legenda'])}</figcaption>
      </figure>
    </div>
    <div id="{cid}-pb" class="clip" data-start="1.3" data-duration="{dur - 1.3:.2f}" data-track-index="4" data-layout-allow-overlap>
      <figure id="{cid}-b" class="ret" style="left:{W - bw - 70}px;top:1150px">
        <img src="assets/{b['arq']}" width="{bw}" height="{bh}" alt="">
        <figcaption>{e(b['legenda'])}</figcaption>
      </figure>
    </div>
    <div id="{cid}-pc" class="clip" data-start="2.3" data-duration="{dur - 2.3:.2f}" data-track-index="5" data-layout-allow-overlap>
      <figure id="{cid}-c" class="ret" style="left:60px;top:1250px">
        <img src="assets/{cc['arq']}" width="{cw}" height="{ch}" alt="">
        <figcaption>{e(cc['legenda'])}</figcaption>
      </figure>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{paused:true}});{entrada_a}{assenta_a}{hora_in}
    tl.fromTo("#{cid}-a", {{x:0}}, {{x:-40, duration:.5, ease:"power2.inOut"}}, 1.3);
    tl.fromTo("#{cid}-b", {{x:700, rotation:10, opacity:0}}, {{x:0, rotation:3, opacity:1, duration:.55, ease:"expo.out"}}, 1.3);
    tl.fromTo("#{cid}-c", {{x:-600, rotation:-12, opacity:0}}, {{x:0, rotation:-4, opacity:1, duration:.55, ease:"expo.out"}}, 2.3);
    // saída: os retratos são arrancados da parede, a hora e a linha se apagam
    const fim = {dur - 0.45:.2f};
    tl.to(["#{cid}-c", "#{cid}-b", "#{cid}-a"], {{x:-900, y:-60, rotation:-14, duration:.35, ease:"power3.in", stagger:.05}}, fim);
    tl.to(["#{cid}-hora", "#{cid}-linha"], {{opacity:0, filter:"blur(8px)", duration:.2, ease:"power2.in"}}, fim + .05);
    window.__timelines["{cid}"] = tl;
  </script>
</template>
'''


def cena_fundo(viradas):
    """Papel do dia que esquenta à tarde, vira madeira à noite e volta no fecho."""
    grao = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='320' height='320'>"
            "<filter id='g'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' seed='7'/>"
            "<feColorMatrix values='0 0 0 0 .35 0 0 0 0 .25 0 0 0 0 .15 0 0 0 .9 0'/></filter>"
            "<rect width='100%' height='100%' filter='url(%23g)'/></svg>")
    t1, t2, t3 = viradas
    return f'''<template>
  <style>
    #fundo-root{{position:absolute;inset:0}}
    #fundo-root .camada{{position:absolute;inset:0}}
    #fundo-dia{{background:{DIA['chao']}}}
    #fundo-tarde{{background:{TARDE['chao']};opacity:0}}
    #fundo-noite{{background:{NOITE['chao']};opacity:0}}
    #fundo-grao{{background-image:url("{grao}");opacity:.06;mix-blend-mode:multiply}}
    #fundo-azulejo{{position:absolute;left:0;right:0;top:1700px;height:44px;
      background-color:rgba(255,250,240,.35);
      background-image:repeating-linear-gradient(45deg,rgba(44,95,138,.38) 0 2px,transparent 2px 20px),
        repeating-linear-gradient(-45deg,rgba(44,95,138,.38) 0 2px,transparent 2px 20px);
      border-top:2px solid rgba(107,69,38,.35);border-bottom:2px solid rgba(107,69,38,.35)}}
  </style>
  <div id="fundo-root" data-composition-id="fundo" data-width="{W}" data-height="{H}">
    <div id="fundo-dia" class="camada"></div>
    <div id="fundo-tarde" class="camada"></div>
    <div id="fundo-noite" class="camada"></div>
    <div id="fundo-azulejo" data-layout-ignore></div>
    <div id="fundo-grao" class="camada" data-layout-ignore></div>
  </div>
  <script>
    const tl = gsap.timeline({{paused:true}});
    tl.fromTo("#fundo-tarde", {{opacity:0}}, {{opacity:1, duration:.5, ease:"power2.inOut"}}, {t1});
    tl.fromTo("#fundo-noite", {{opacity:0}}, {{opacity:1, duration:.5, ease:"power2.inOut"}}, {t2});
    tl.to(["#fundo-noite", "#fundo-tarde"], {{opacity:0, duration:.5, ease:"power2.inOut"}}, {t3});
    tl.to("#fundo-azulejo", {{opacity:.25, duration:.5, ease:"power2.inOut"}}, {t2});
    tl.to("#fundo-azulejo", {{opacity:1, duration:.5, ease:"power2.inOut"}}, {t3});
    window.__timelines["fundo"] = tl;
  </script>
</template>
'''


def angulos(hhmm):
    h, m = (int(x) for x in hhmm.split(':'))
    return h * 60 + m


def cena_relogio(horarios, varreduras, saida):
    """Relógio de parede: cada varredura do ponteiro é a causa da troca de hora."""
    tracos = []
    for i in range(60):
        grosso = i % 5 == 0
        tracos.append(f'<line x1="200" y1="{38 if grosso else 42}" x2="200" y2="{62 if grosso else 52}" '
                      f'stroke="#2d1e13" stroke-width="{5 if grosso else 2}" stroke-linecap="round" '
                      f'transform="rotate({i * 6} 200 200)"/>')
    nums = ''.join(f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="central" '
                   f'font-family="Playfair Display" font-weight="900" font-size="52" fill="#2d1e13">{n}</text>'
                   for n, x, y in (('12', 200, 98), ('3', 304, 202), ('6', 200, 306), ('9', 96, 202)))
    minutos = [angulos(h) for h in horarios]
    m0 = minutos[0]
    passos = []
    for (ini, dur), alvo in zip(varreduras, minutos[1:]):
        passos.append(f'''
    tl.to("#rel-min", {{rotation:{(alvo - m0) * 6 + (m0 % 60) * 6}, duration:{dur}, ease:"power2.inOut"}}, {ini});
    tl.to("#rel-hor", {{rotation:{alvo * 0.5}, duration:{dur}, ease:"power2.inOut"}}, {ini});''')
    return f'''<template>
  <style>
    #relogio-root{{position:absolute;inset:0}}
    #rel-caixa{{position:absolute;left:340px;top:190px;width:400px;height:400px}}
    #rel-caixa svg{{display:block;width:400px;height:400px;filter:drop-shadow(0 16px 30px rgba(0,0,0,.25))}}
  </style>
  <div id="relogio-root" data-composition-id="relogio" data-width="{W}" data-height="{H}">
    <div id="rel-clip" class="clip" data-start="0" data-duration="{saida + 0.6}" data-track-index="1">
      <div id="rel-caixa">
        <svg viewBox="0 0 400 400" aria-hidden="true">
          <circle cx="200" cy="200" r="196" fill="#6b4526"/>
          <circle cx="200" cy="200" r="168" fill="#43290f"/>
          <circle cx="200" cy="200" r="164" fill="#fffaf0"/>
          {''.join(tracos)}
          {nums}
          <g id="rel-hor"><rect x="192" y="88" width="16" height="124" rx="8" fill="#b32a1e"/></g>
          <g id="rel-min"><rect x="195.5" y="34" width="9" height="178" rx="4.5" fill="#b32a1e"/></g>
          <circle cx="200" cy="200" r="11" fill="#43290f"/>
        </svg>
      </div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{paused:true}});
    tl.set("#rel-min", {{rotation:{(m0 % 60) * 6}, svgOrigin:"200 200"}}, 0);
    tl.set("#rel-hor", {{rotation:{m0 * 0.5}, svgOrigin:"200 200"}}, 0);{''.join(passos)}
    // o relógio encolhe até o lugar da placa da marca e some nela
    tl.to("#rel-caixa", {{scale:.62, y:-20, duration:.5, ease:"power3.in"}}, {saida});
    tl.to("#rel-caixa", {{opacity:0, duration:.18, ease:"power2.in"}}, {saida + 0.36});
    window.__timelines["relogio"] = tl;
  </script>
</template>
'''


def cena_fecho(d):
    dur = FECHO[1]
    # mural de baixo: um retrato pequeno de cada hora do dia (decoração, fora da faixa de texto)
    giros = (-5, 3, -2)
    mural = ''.join(
        f'<figure class="mr" style="left:{60 + i * 330}px;transform:rotate({giros[i]}deg)">'
        f'<img src="assets/{c["fotos"][0]["arq"]}" width="276" height="184" alt=""></figure>'
        for i, c in enumerate(d['horas']))
    return f'''<template>
  <style>
    #fecho-root{{position:absolute;inset:0;font-family:"Playfair Display",serif;color:{DIA['tinta']}}}
    #fecho-placa{{position:absolute;left:406px;top:220px;width:268px;height:268px;padding:14px;
      background:#fffaf0;box-shadow:0 18px 40px rgba(61,36,21,.30)}}
    #fecho-placa img{{display:block;width:240px;height:240px;object-fit:contain}}
    #fecho-mural{{position:absolute;left:0;right:0;top:1420px;height:420px}}
    #fecho-mural .mr{{position:absolute;top:0;background:#fffaf0;padding:12px 12px 40px;
      box-shadow:0 14px 30px rgba(61,36,21,.28)}}
    #fecho-mural .mr img{{display:block;width:276px;height:184px;object-fit:cover}}
    #fecho-nome{{position:absolute;left:96px;top:580px;width:888px;font-weight:900;font-size:150px;line-height:.95;letter-spacing:-.015em}}
    #fecho-nome em{{display:block;font-style:italic;font-weight:700;color:{DIA['madeira']}}}
    #fecho-linha{{position:absolute;left:96px;top:930px;width:888px;font-weight:700;font-size:48px;line-height:1.2}}
    #fecho-pede{{position:absolute;left:96px;top:1100px;width:888px}}
    #fecho-pede b{{display:block;font-weight:700;font-size:44px;line-height:1.2}}
    #fecho-pede span{{display:block;font-weight:900;font-size:84px;line-height:1.1;color:{DIA['esmalte']};letter-spacing:-.01em}}
  </style>
  <div id="fecho-root" data-composition-id="fecho" data-width="{W}" data-height="{H}">
    <div id="fecho-pl" class="clip" data-start="0" data-duration="{dur}" data-track-index="1">
      <div id="fecho-placa"><img src="assets/{d['logo']}" width="240" height="240" alt=""></div>
    </div>
    <h1 id="fecho-nome" class="clip" data-start="0" data-duration="{dur}" data-track-index="2"><span id="fecho-n1">{e(d['nome1'])}</span><em id="fecho-n2">{e(d['nome2'])}</em></h1>
    <p id="fecho-linha" class="clip" data-start="0" data-duration="{dur}" data-track-index="3">{palavras(d['fecho_linha'], 'fecho')}</p>
    <div id="fecho-mu" class="clip" data-start="0" data-duration="{dur}" data-track-index="5" data-layout-ignore>
      <div id="fecho-mural">{mural}</div>
    </div>
    <div id="fecho-pede" class="clip" data-start="0" data-duration="{dur}" data-track-index="4"><b id="fecho-pb">Peça pelo WhatsApp</b><span id="fecho-zap">{e(d['whatsapp'])}</span></div>
  </div>
  <script>
    const tl = gsap.timeline({{paused:true}});
    tl.fromTo("#fecho-placa", {{scale:.62, rotation:0, opacity:0}}, {{scale:1, rotation:-2, opacity:1, duration:.55, ease:"expo.out"}}, 0);
    tl.fromTo("#fecho-n1", {{opacity:.3, filter:"blur(6px)"}}, {{opacity:1, filter:"blur(0px)", duration:.2, ease:"power4.out"}}, .3);
    tl.fromTo("#fecho-n2", {{opacity:.3, filter:"blur(6px)"}}, {{opacity:1, filter:"blur(0px)", duration:.2, ease:"power4.out"}}, .42);
    tl.fromTo("#fecho-linha .fecho-p", {{opacity:0, filter:"blur(6px)"}}, {{opacity:1, filter:"blur(0px)", duration:.13, ease:"power4.out", stagger:.07}}, .7);
    tl.fromTo("#fecho-pb", {{opacity:0}}, {{opacity:1, duration:.2, ease:"power2.out"}}, 1.05);
    tl.fromTo("#fecho-zap", {{opacity:0, x:-24}}, {{opacity:1, x:0, duration:.45, ease:"expo.out"}}, 1.15);
    tl.fromTo("#fecho-mural .mr", {{y:220, opacity:0}}, {{y:0, opacity:1, duration:.55, ease:"expo.out", stagger:.08}}, .2);
    window.__timelines["fecho"] = tl;
  </script>
</template>
'''


def index(d):
    hosts = [
        ('fundo', 0, TOTAL, 0),
        ('hora1', JANELAS[0][0], JANELAS[0][1], 2),
        ('hora2', JANELAS[1][0], JANELAS[1][1], 3),
        ('hora3', JANELAS[2][0], JANELAS[2][1], 4),
        ('relogio', 0, 11.8, 5),
        ('fecho', FECHO[0], FECHO[1], 6),
    ]
    divs = '\n'.join(
        f'      <div id="{h}" data-composition-id="{h}" data-composition-src="compositions/{h}.html" '
        f'data-start="{s}" data-duration="{du}" data-track-index="{tr}" data-track-kind="graphics" '
        f'data-width="{W}" data-height="{H}" style="z-index:{tr + 1}"></div>' for h, s, du, tr in hosts)
    return f'''<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <title>{e(d['nome'])} — um dia na esquina</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ width:{W}px; height:{H}px; overflow:hidden; background:{DIA['chao']}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="{W}" data-height="{H}">
{divs}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
'''


def montar(roteiro):
    d = json.load(open(roteiro, encoding='utf-8'))
    saida = os.path.join(AQUI, 'saida', d['slug'])
    comp = os.path.join(saida, 'compositions')
    ass = os.path.join(saida, 'assets')
    os.makedirs(comp, exist_ok=True)
    os.makedirs(ass, exist_ok=True)
    # fotos: copia do static do site, mede e confere que nenhuma será ampliada
    from PIL import Image
    for c in d['horas']:
        for f in c['fotos']:
            orig = os.path.join(STATIC, f['src'])
            f['arq'] = os.path.basename(f['src'])
            shutil.copy(orig, os.path.join(ass, f['arq']))
            f['w'], f['h'] = Image.open(orig).size
    shutil.copy(os.path.join(STATIC, d['logo_src']), os.path.join(ass, os.path.basename(d['logo_src'])))
    d['logo'] = os.path.basename(d['logo_src'])

    pals = [DIA, TARDE, NOITE]
    for i, c in enumerate(d['horas']):
        open(os.path.join(comp, f'hora{i + 1}.html'), 'w', encoding='utf-8').write(
            cena_hora(f'hora{i + 1}', i, c, pals[i], i == 0))
    open(os.path.join(comp, 'fundo.html'), 'w', encoding='utf-8').write(cena_fundo((3.45, 7.25, 11.05)))
    open(os.path.join(comp, 'relogio.html'), 'w', encoding='utf-8').write(
        cena_relogio([c['relogio'] for c in d['horas']], [(3.3, 1.0), (7.1, 1.0)], 11.0))
    open(os.path.join(comp, 'fecho.html'), 'w', encoding='utf-8').write(cena_fecho(d))
    open(os.path.join(saida, 'index.html'), 'w', encoding='utf-8').write(index(d))
    for arq in ('hyperframes.json', 'package.json', 'SPEC.md'):
        src = os.path.join(AQUI, 'venda-vertical', arq)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(saida, arq))
    json.dump({'id': f"{d['slug']}-dia-na-esquina", 'name': f"{d['nome']} — um dia na esquina"},
              open(os.path.join(saida, 'meta.json'), 'w'), ensure_ascii=False)
    print(saida)


if __name__ == '__main__':
    montar(sys.argv[1])
