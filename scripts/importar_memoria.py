"""Junta rascunhos de verbetes e gera os dados da Memória Viva.

    venv/bin/python scripts/importar_memoria.py RASCUNHO.yml [...] \
        --fotos "/home/dan/Documentos/SCRAP BARAO" [--mural MURAL.yml ...]

Para cada verbete com `foto.arquivo`, procura a imagem em
`<fotos>/barao_posts/imagens/` ou `<fotos>/wikipedia_barao/imagens/`, gera
WebP de 800 e 400 px em `app/static/img/memoria/<slug>-{800,400}.webp` e grava
`foto.webp: <slug>`. Escreve `app/data/memoria/verbetes.yml` e `mural.yml`.
Recusa verbete sem fonte ou com slug repetido.
"""
import argparse
import os
import sys

import yaml
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_DADOS = os.path.join(RAIZ, 'app', 'data', 'memoria')
DIR_IMG = os.path.join(RAIZ, 'app', 'static', 'img', 'memoria')


def _achar_foto(base, arquivo):
    for sub in ('barao_posts/imagens', 'wikipedia_barao/imagens'):
        caminho = os.path.join(base, sub, arquivo)
        if os.path.exists(caminho):
            return caminho
    return None


def _webp(origem, slug):
    with Image.open(origem) as im:
        im = im.convert('RGB')
        for largura in (800, 400):
            copia = im.copy()
            if copia.width > largura:
                copia = copia.resize((largura, round(copia.height * largura / copia.width)))
            copia.save(os.path.join(DIR_IMG, f'{slug}-{largura}.webp'), 'WEBP', quality=78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rascunhos', nargs='+')
    ap.add_argument('--fotos', required=True)
    ap.add_argument('--mural', nargs='*', default=[])
    args = ap.parse_args()

    os.makedirs(DIR_DADOS, exist_ok=True)
    os.makedirs(DIR_IMG, exist_ok=True)
    todos, vistos, problemas = [], set(), []
    for arq in args.rascunhos:
        for v in yaml.safe_load(open(arq, encoding='utf-8')) or []:
            if v['slug'] in vistos:
                problemas.append(f"slug repetido: {v['slug']}")
                continue
            if not v.get('fontes'):
                problemas.append(f"sem fonte: {v['slug']}")
                continue
            vistos.add(v['slug'])
            foto = v.get('foto') or {}
            if foto.get('arquivo'):
                origem = _achar_foto(args.fotos, foto['arquivo'])
                if origem:
                    _webp(origem, v['slug'])
                    foto['webp'] = v['slug']
                else:
                    problemas.append(f"foto não encontrada: {foto['arquivo']} ({v['slug']})")
            todos.append(v)

    mural = []
    for arq in args.mural:
        mural += [m for m in (yaml.safe_load(open(arq, encoding='utf-8')) or [])
                  if m.get('verbete') in vistos or not m.get('verbete')]

    cabecalho = ('# Gerado por scripts/importar_memoria.py a partir dos rascunhos revisados.\n'
                 '# Pode editar à mão; ao reimportar, este arquivo é sobrescrito.\n')
    with open(os.path.join(DIR_DADOS, 'verbetes.yml'), 'w', encoding='utf-8') as f:
        f.write(cabecalho)
        yaml.safe_dump(todos, f, allow_unicode=True, sort_keys=False, width=100)
    with open(os.path.join(DIR_DADOS, 'mural.yml'), 'w', encoding='utf-8') as f:
        f.write(cabecalho)
        yaml.safe_dump(mural, f, allow_unicode=True, sort_keys=False, width=100)

    print(f'{len(todos)} verbetes, {len(mural)} memórias no mural')
    for p in problemas:
        print('  !', p)
    return 1 if any(p.startswith(('slug', 'sem fonte')) for p in problemas) else 0


if __name__ == '__main__':
    sys.exit(main())
