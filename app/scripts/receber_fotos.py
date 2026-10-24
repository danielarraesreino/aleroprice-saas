"""Recebe as fotos originais de um expositor e as encaixa no hotsite dele.

    python -m app.scripts.receber_fotos ~/Documentos/FEIRADEBARAO/fotos-recebidas --dry-run
    python -m app.scripts.receber_fotos ~/Documentos/FEIRADEBARAO/fotos-recebidas

Estrutura da pasta recebida: uma subpasta por expositor, com o slug do site:

    fotos-recebidas/
      fermentei/
        AUTORIZADO.txt          <- obrigatório: quem autorizou, quando, por onde
        capa.jpg                <- foto do topo
        logo.png                <- marca (se tiver)
        produto-pao-de-forma.jpg
        qualquer-outra.jpg      <- vai para a galeria

Regras:
- **Sem `AUTORIZADO.txt` a pasta é ignorada.** Foto de terceiro não entra no site sem
  registro de autorização (basta uma linha: "Autorizado por <nome> no WhatsApp em 21/10").
- **Só imagem grande entra.** Lado menor abaixo de 800 px (300 px no logo) é recusado:
  captura de tela e foto de WhatsApp comprimida ficam borradas no site.
- Saída em `app/static/img/demo/<slug>/` (convenção do `fotos_do_bar`), JPEG otimizado,
  EXIF respeitado, sem cortar (exceto logo, quadrado).
- `produto-<nome>.jpg` casa com o produto de mesmo nome no `.yml`; sem par, vira
  produto novo. Depois: `/bootstrap-demo?action=demos&slug=<slug>` (ou o botão do campo).
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.scripts.importar_expositores import DIR_LEADS  # noqa: E402

DIR_FOTOS = Path(__file__).resolve().parents[1] / 'static' / 'img' / 'demo'
EXT = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
MIN_LADO = 800
MIN_LADO_LOGO = 300
MAX_LADO = {'capa': 1600, 'produto': 1000, 'galeria': 1000}


def _slug(texto):
    base = unicodedata.normalize('NFKD', str(texto or ''))
    base = ''.join(c for c in base if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', '-', base).strip('-')


def _papel(nome_arquivo):
    """capa | logo | produto | galeria, pelo nome (sem extensão)."""
    base = Path(nome_arquivo).stem.lower()
    if base in ('capa', 'hero', '00-capa'):
        return 'capa', ''
    if base == 'logo':
        return 'logo', ''
    if base.startswith('produto-') or base.startswith('produto_'):
        return 'produto', _slug(base[8:])
    return 'galeria', ''


def _abrir(caminho):
    from PIL import Image, ImageOps
    im = Image.open(caminho)
    im = ImageOps.exif_transpose(im)
    return im.convert('RGB')


def _salvar(im, destino, max_lado=None, quadrado=False):
    from PIL import Image
    if quadrado:
        lado = min(im.size)
        esq, topo = (im.width - lado) // 2, (im.height - lado) // 2
        im = im.crop((esq, topo, esq + lado, topo + lado)).resize((512, 512), Image.LANCZOS)
    elif max_lado and max(im.size) > max_lado:
        im.thumbnail((max_lado, max_lado), Image.LANCZOS)
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, 'JPEG', quality=82, optimize=True, progressive=True)


def _atualizar_lead(arquivo, produtos_com_foto, dry_run):
    """Põe `imagem` nos produtos do .yml (por nome); sem par, acrescenta o produto."""
    import yaml
    if not arquivo.exists() or not produtos_com_foto:
        return []
    lead = yaml.safe_load(arquivo.read_text(encoding='utf-8')) or {}
    itens = lead.setdefault('produtos', [])
    log = []
    for chave, (rotulo, caminho) in produtos_com_foto.items():
        par = next((p for p in itens if _slug(p.get('nome')) == chave), None) or \
              next((p for p in itens if chave and (chave in _slug(p.get('nome')) or _slug(p.get('nome')) in chave)), None)
        if par is not None:
            par['imagem'] = caminho
            log.append(f'produto "{par["nome"]}" ganhou foto')
        else:
            itens.append({'nome': rotulo, 'imagem': caminho})
            log.append(f'produto novo "{rotulo}" (sem par no .yml)')
    if not dry_run:
        arquivo.write_text(yaml.safe_dump(lead, allow_unicode=True, sort_keys=False, width=100),
                           encoding='utf-8')
    return log


def receber(pasta, dry_run=False, destino_fotos=None, dir_leads=None):
    """Processa cada subpasta. Devolve [{slug, status, feitos, recusados, avisos}]."""
    destino_fotos = Path(destino_fotos or DIR_FOTOS)
    dir_leads = Path(dir_leads or DIR_LEADS)
    resultado = []
    for sub in sorted(p for p in Path(pasta).iterdir() if p.is_dir()):
        slug = sub.name
        r = {'slug': slug, 'status': 'ok', 'feitos': [], 'recusados': [], 'avisos': []}
        resultado.append(r)
        aut = sub / 'AUTORIZADO.txt'
        if not aut.exists() or not aut.read_text(encoding='utf-8', errors='ignore').strip():
            r['status'] = 'ignorada: falta AUTORIZADO.txt (quem autorizou, quando, por onde)'
            continue
        produtos, n_galeria = {}, 0
        for arq in sorted(sub.iterdir()):
            if arq.suffix.lower() not in EXT:
                continue
            papel, nome = _papel(arq.name)
            try:
                im = _abrir(arq)
            except Exception as e:                       # arquivo corrompido, HEIC sem suporte
                r['recusados'].append(f'{arq.name}: não abriu ({type(e).__name__})')
                continue
            minimo = MIN_LADO_LOGO if papel == 'logo' else MIN_LADO
            if min(im.size) < minimo:
                r['recusados'].append(f'{arq.name}: {im.width}x{im.height} é pequena (mínimo {minimo}px no lado menor)')
                continue
            if papel == 'capa':
                saida = destino_fotos / slug / 'capa.jpg'
                kw = {'max_lado': MAX_LADO['capa']}
            elif papel == 'logo':
                saida = destino_fotos / slug / 'logo.jpg'
                kw = {'quadrado': True}
            elif papel == 'produto':
                saida = destino_fotos / slug / f'produto-{nome or "produto"}.jpg'
                kw = {'max_lado': MAX_LADO['produto']}
                produtos[nome] = (nome.replace('-', ' ').capitalize(), f'img/demo/{slug}/{saida.name}')
            else:
                n_galeria += 1
                saida = destino_fotos / slug / f'galeria-{n_galeria:02d}.jpg'
                kw = {'max_lado': MAX_LADO['galeria']}
            if not dry_run:
                _salvar(im, saida, **kw)
            r['feitos'].append(f'{arq.name} -> {saida.name}')
        r['avisos'] += _atualizar_lead(dir_leads / f'{slug}.yml', produtos, dry_run)
        if not r['feitos']:
            r['status'] = 'nada aproveitável'
    return resultado


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('pasta', help='pasta com uma subpasta por expositor (nome = slug do site)')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args(argv)
    for r in receber(args.pasta, args.dry_run):
        print(f"[{r['status']}] {r['slug']}: {len(r['feitos'])} foto(s)")
        for linha in r['feitos'] + r['avisos']:
            print(f'    + {linha}')
        for linha in r['recusados']:
            print(f'    - RECUSADA {linha}')


if __name__ == '__main__':
    main()
