#!/usr/bin/env python3
"""design-10k / secao 7 — mede diferenciacao entre modelos de landing.

uso: python3 bin/diferenciacao.py app/templates/site/modelos/*.html app/templates/site/landing.html

Metas:
  - Jaccard de CONJUNTO de secoes <= 0,80 em todo par
  - caudas (ultimas 3 secoes) distintas >= n-1
  - >= 4 dos 7 eixos diferindo em cada par
"""
import re
import sys
import itertools
import pathlib

SEC = re.compile(r'<section[^>]*\bid="([a-z-]+)"')


def seq(p):
    return SEC.findall(pathlib.Path(p).read_text(errors="ignore"))


def J(A, B):
    return len(A & B) / len(A | B) if A | B else 1.0


# ---------- eixos (secao 7.2) -------------------------------------------------
# 1 heroina  2 ordem/cauda  3 eixo de leitura  4 densidade
# 5 tratamento de foto  6 escala tipografica  7 paleta
def eixos(p):
    t = pathlib.Path(p).read_text(errors="ignore")
    s = seq(p)

    def v(nome, padrao=""):
        m = re.search(r'--' + nome + r'\s*:\s*([^;}]+)', t)
        return m.group(1).strip() if m else padrao

    return {
        "heroina": (re.search(r'data-heroina="([a-z-]+)"', t) or [None, s[0] if s else ""])[1],
        "cauda": " > ".join(s[-3:]),
        "leitura": (re.search(r'data-leitura="([a-z-]+)"', t) or [None, ""])[1],
        "densidade": v("sec-y"),
        "foto": (re.search(r'data-foto="([a-z-]+)"', t) or [None, ""])[1],
        "tipo": v("t-display"),
        "paleta": v("acento") or v("bg"),
    }


def main():
    fs = sys.argv[1:]
    if not fs:
        print(__doc__)
        return 1

    falhas = []
    print("conj.  ordem  eixos  par")
    for a, b in itertools.combinations(fs, 2):
        sa, sb = seq(a), seq(b)
        js = J(set(sa), set(sb))
        jo = J(set(zip(sa, sa[1:])), set(zip(sb, sb[1:])))
        ea, eb = eixos(a), eixos(b)
        dif = sum(1 for k in ea if ea[k] != eb[k])
        na, nb = pathlib.Path(a).stem, pathlib.Path(b).stem
        tag = "CLONE" if js > .8 else ("eixo<4" if dif < 4 else "ok")
        if js > .8:
            falhas.append(f"jaccard {js:.0%} em {na} x {nb}")
        if dif < 4:
            falhas.append(f"so {dif}/7 eixos em {na} x {nb}")
        print(f"{js:5.0%}  {jo:5.0%}  {dif}/7    {tag:6s} {na} x {nb}")

    print()
    t = {}
    for f in fs:
        c = " > ".join(seq(f)[-3:])
        t[c] = t.get(c, 0) + 1
        print(f"cauda  {pathlib.Path(f).stem:13s} {c}")

    minimo = len(fs) - 1
    print(f"\ncaudas distintas: {len(t)}/{len(fs)}  (min exigido: {minimo})")
    if len(t) < minimo:
        falhas.append(f"caudas distintas {len(t)} < {minimo}")

    print()
    for f in fs:
        e = eixos(f)
        print(f"eixos  {pathlib.Path(f).stem:13s} heroina={e['heroina']:11s} "
              f"leitura={e['leitura']:12s} foto={e['foto']:11s} sec-y={e['densidade']}")

    print()
    if falhas:
        print(f"FALHA ({len(falhas)}):")
        for x in falhas:
            print("  -", x)
        return 1
    print("OK — todos os pares passam.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
