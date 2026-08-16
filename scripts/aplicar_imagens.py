"""Pega imagem solta e entrega pronta para o site.

O passo que era manual: baixar do gerador, redimensionar, converter, renomear na
convenção certa e ligar ao lead. Fiz isso à mão para o Bar da Vila e para o Bar
do Zé; a partir daqui é um comando.

O que ele faz, e por quê
------------------------
1. **Otimiza.** JPEG progressivo, 1600px de largura, quality 82. Medido no Bar
   do Zé: 7 MB de PNG viraram 197 KB. O hero é a primeira coisa que carrega no
   4G do bar — 7 MB ali é o dono fechando a aba antes de ver o site dele.

2. **Nomeia na convenção que o aplicador já lê** (`app/utils/demos.py:108`):
   `capa.jpg` vira o topo, `prato-<nome>.jpg` entra no cardápio, o resto vai
   pra galeria. Arquivo fora da convenção é foto que não aparece em lugar nenhum.

3. **Liga ao lead.** Escreve `hero_foto` no `site:` e, quando o nome do arquivo
   casa com um prato existente, o `imagem:` daquele item. Sem isso o aplicador
   cria um item NOVO com o nome do arquivo e o cardápio duplica.

4. **Grava `creditos.json`.** Imagem de banco costuma exigir atribuição; imagem
   gerada é bom saber de onde veio. Sem registro, seis meses depois ninguém sabe
   o que pode publicar.

Como usar
---------
    python3 scripts/aplicar_imagens.py bronco-burger
    python3 scripts/aplicar_imagens.py bronco-burger --fonte 'Higgsfield Soul 2.0'
    python3 scripts/aplicar_imagens.py --todos --seco

`--seco` mostra o que faria sem tocar em nada. Rode antes na primeira vez.

Idempotente: rodar duas vezes não estraga nada — imagem já otimizada é
reconhecida pelo tamanho e pulada.
"""
import argparse
import glob
import json
import os
import re
import sys

try:
    from PIL import Image
except ImportError:
    print('Falta o Pillow:  pip install Pillow')
    sys.exit(2)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_LEADS = os.path.join(REPO, 'app', 'data', 'leads')
DIR_FOTOS = os.path.join(REPO, 'app', 'static', 'img', 'demo')

LARGURA = 1600      # cobre retina de celular sem virar download pesado
QUALIDADE = 82      # abaixo disso aparece bloco no degradê da luz âmbar
EXTENSOES = ('.jpg', '.jpeg', '.png', '.webp')


def otimizar(caminho):
    """Converte para JPEG progressivo e reduz. Devolve (antes, depois) em bytes."""
    antes = os.path.getsize(caminho)
    with Image.open(caminho) as im:
        im = im.convert('RGB')
        if im.width > LARGURA:
            im.thumbnail((LARGURA, LARGURA * 4), Image.LANCZOS)
        destino = os.path.splitext(caminho)[0] + '.jpg'
        im.save(destino, 'JPEG', quality=QUALIDADE, optimize=True, progressive=True)
    # PNG/webp viram .jpg: o original sai, senão a pasta fica com os dois e o
    # aplicador conta a mesma foto duas vezes na galeria.
    if destino != caminho:
        os.remove(caminho)
    return antes, os.path.getsize(destino), destino


def _norm(texto):
    import unicodedata
    t = unicodedata.normalize('NFD', (texto or '').lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def ligar_no_lead(slug, arquivos, seco=False):
    """Grava hero_foto e o `imagem:` dos pratos que casarem pelo nome."""
    caminho = os.path.join(DIR_LEADS, f'{slug}.yml')
    if not os.path.isfile(caminho):
        return ['(sem arquivo de lead — nada a ligar)']
    texto = open(caminho, encoding='utf-8').read()
    feitos = []

    capa = next((a for a in arquivos if os.path.basename(a) == 'capa.jpg'), None)
    # Procura o CAMPO, não a palavra: os leads explicam no comentário do topo
    # por que não têm `hero_foto`, e um `in texto` casava com esse comentário —
    # o script dizia "já está apontado" e a capa nunca era ligada.
    ja_tem_hero = re.search(r'^\s+hero_foto:', texto, re.M)
    if capa and not ja_tem_hero:
        linha = f'  hero_foto: "img/demo/{slug}/capa.jpg"'
        # entra logo depois de `site:`, que é onde moram os campos do SiteConfig
        texto = re.sub(r'^(site:\n)', rf'\1{linha}\n', texto, count=1, flags=re.M)
        feitos.append('hero_foto')

    # prato-<slug-do-nome>.jpg -> o item cujo nome bate
    for arq in arquivos:
        base = os.path.basename(arq)
        if not base.startswith('prato-'):
            continue
        alvo_slug = base[len('prato-'):-len('.jpg')]
        for m in re.finditer(r'^  - nome: "([^"]+)"$', texto, re.M):
            if _norm(m.group(1)) != alvo_slug:
                continue
            bloco_ini = m.end()
            prox = texto.find('\n  - nome:', bloco_ini)
            bloco = texto[bloco_ini:prox if prox != -1 else len(texto)]
            if 'imagem:' in bloco:
                break   # já tem foto: respeita
            linha = f'\n    imagem: "img/demo/{slug}/{base}"'
            texto = texto[:m.end()] + linha + texto[m.end():]
            feitos.append(f'imagem de "{m.group(1)}"')
            break

    if feitos and not seco:
        open(caminho, 'w', encoding='utf-8').write(texto)
    return feitos or ['(nada a ligar — já estava tudo apontado)']


def processar(slug, fonte, seco=False):
    pasta = os.path.join(DIR_FOTOS, slug)
    if not os.path.isdir(pasta):
        print(f'  {slug}: pasta não existe ({pasta})')
        return False

    brutos = [f for f in sorted(glob.glob(os.path.join(pasta, '*')))
              if f.lower().endswith(EXTENSOES)]
    if not brutos:
        print(f'  {slug}: pasta vazia')
        return False

    print(f'\n{slug}')
    finais, creditos = [], []
    for arq in brutos:
        if seco:
            print(f'  · {os.path.basename(arq)} '
                  f'({os.path.getsize(arq)//1024} KB) — seria otimizado')
            finais.append(arq)
            continue
        antes, depois, destino = otimizar(arq)
        marca = '' if antes == depois else f'  {antes//1024} KB -> {depois//1024} KB'
        print(f'  · {os.path.basename(destino):34}{marca}')
        finais.append(destino)
        creditos.append({'arquivo': os.path.basename(destino), 'fonte': fonte})

    for feito in ligar_no_lead(slug, finais, seco=seco):
        print(f'    lead: {feito}')

    if creditos and not seco:
        cred = os.path.join(pasta, 'creditos.json')
        antigos = []
        if os.path.exists(cred):
            try:
                antigos = json.load(open(cred, encoding='utf-8'))
            except (ValueError, OSError):
                antigos = []
        conhecidos = {c.get('arquivo') for c in antigos}
        novos = [c for c in creditos if c['arquivo'] not in conhecidos]
        if novos:
            with open(cred, 'w', encoding='utf-8') as f:
                json.dump(antigos + novos, f, ensure_ascii=False, indent=1)
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('slugs', nargs='*')
    p.add_argument('--todos', action='store_true', help='toda pasta em img/demo')
    p.add_argument('--fonte', default='gerada por IA',
                   help='de onde vieram as imagens (vai pro creditos.json)')
    p.add_argument('--seco', action='store_true', help='mostra sem alterar nada')
    a = p.parse_args()

    alvos = a.slugs
    if a.todos:
        alvos = sorted(os.path.basename(d) for d in glob.glob(os.path.join(DIR_FOTOS, '*'))
                       if os.path.isdir(d))
    if not alvos:
        p.error('diga um slug ou use --todos')

    if a.seco:
        print('MODO SECO — nada é alterado\n')
    feitos = sum(1 for s in alvos if processar(s, a.fonte, seco=a.seco))
    print(f'\n{feitos} de {len(alvos)} pasta(s) processada(s)')

    if not a.seco and feitos:
        print('\nPara ver no site:')
        print('  flask --app app aplicar-demos && python run.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
