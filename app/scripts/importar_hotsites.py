"""Pacote de hotsites (expositores.json) -> um lead `.yml` por expositor.

    python -m app.scripts.importar_hotsites /caminho/expositores.json --dry-run
    python -m app.scripts.importar_hotsites /caminho/expositores.json

Cada lead usa o mesmo pipeline das prévias de bar (`/bootstrap-demo?action=demos`):
nasce `noindex`, com aviso de "prévia não oficial", e expira se ninguém converter.

Escolhas deste importador, todas por segurança de conteúdo:
- **Fotos não entram.** As do pacote são capturas de tela do Instagram (~230x310 px)
  e ninguém autorizou o uso. O hotsite nasce sem foto (lista em texto) e ganha a
  foto original quando o expositor mandar e autorizar.
- **Só o que a pessoa publicou**: bio, o que vende, WhatsApp, Instagram e dias. Texto
  de apelo ("sem química", "produção limitada") não é inventado; a vibe usada
  (`artesanal-feira`) é neutra.
- Sem e-mail e sem nome pessoal: o `.yml` é versionado no git.
- Quem já tem lead (a Dona Berga, por exemplo) é pulado; `--force` sobrescreve.
- O modelo (layout) vem da categoria declarada; troque no `.yml` ou no painel.
"""
import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.scripts.importar_expositores import (  # noqa: E402
    DIR_LEADS, horario_da_feira, telefone_exibicao, url_instagram, whatsapp_digitos,
)
from app.utils.modelos import modelo_para_categoria  # noqa: E402
from app.utils.site_router import gerar_slug  # noqa: E402

VALIDADE_DIAS = 60
PULAR = {'dona-berga'}          # já tem site de verdade


def _texto(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def _produto(bruto):
    """'Empadas (frango, palmito)' -> nome 'Empadas', descricao 'Frango, palmito'."""
    t = _texto(bruto)
    m = re.match(r'^(.*?)\s*\((.*)\)\s*$', t)
    nome, desc = (m.group(1), m.group(2)) if m else (t, None)
    nome = nome.strip(' -–;,')[:120]
    if not nome:
        return None
    item = {'nome': nome[:1].upper() + nome[1:]}
    if desc:
        desc = desc.strip()
        item['descricao'] = desc[:1].upper() + desc[1:]
    return item


def converter(e):
    """Um expositor do JSON -> (slug, lead, avisos)."""
    avisos = []
    nome = _texto(e.get('nome'))
    if not nome:
        return None
    slug = e.get('slug') or gerar_slug(nome)
    zap = whatsapp_digitos(e.get('whatsapp'))
    obs = _texto(e.get('obs')).casefold()
    if 'validar' in obs and ('linktree' in obs or 'whatsapp' in obs):
        avisos.append('WhatsApp OMITIDO: o pacote traz dois números diferentes; valide e ponha no .yml')
        zap = None
    if not zap:
        avisos.append('sem WhatsApp: o botão principal vira Instagram')
    ig = url_instagram(e.get('instagram_url') or e.get('ig'))
    if not ig and not zap:
        avisos.append('sem WhatsApp nem Instagram: sem como falar com a pessoa')
    if 'validar' in _texto(e.get('obs')).casefold():
        avisos.append('validar antes de publicar: ' + _texto(e.get('obs')))

    categoria = _texto(e.get('cat'))
    site = {
        'vibe': 'artesanal-feira',
        'modelo': modelo_para_categoria(categoria),
        'tagline': _texto(e.get('bio'))[:300] or None,
        'descritor': categoria[:80] or None,
        'whatsapp': zap,
        'telefone_exibicao': telefone_exibicao(zap),
        'instagram_url': ig,
        'horario': horario_da_feira(e.get('dias')),
        'cidade_uf': 'Barão Geraldo, Campinas–SP',
        'maps_query': 'Feira de Barão Geraldo Campinas',
        'tema_modo': 'auto',
    }
    site = {k: v for k, v in site.items() if v}

    produtos = [p for p in (_produto(x) for x in e.get('vende') or []) if p]
    if not produtos:
        avisos.append('nenhum produto listado')
    if e.get('fotos'):
        avisos.append(f"{len(e['fotos'])} foto(s) do pacote NÃO usadas (captura do Instagram, sem autorização)")

    lead = {
        'nome': nome, 'tipo_negocio': 'artesao', 'site': site,
        'produtos': produtos,
        'demo': {'fonte': 'pacote-hotsites-2026-10',
                 'expira_em': (date.today() + timedelta(days=VALIDADE_DIAS)).isoformat()},
    }
    if not produtos:
        lead.pop('produtos')
    return slug, lead, avisos


def importar(caminho, dry_run=False, force=False, destino=None):
    import yaml
    destino = Path(destino or DIR_LEADS)
    dados = json.loads(Path(caminho).read_text(encoding='utf-8'))
    resultado = []
    for e in dados:
        conv = converter(e)
        if conv is None:
            continue
        slug, lead, avisos = conv
        arquivo = destino / f'{slug}.yml'
        if slug in PULAR:
            resultado.append({'slug': slug, 'status': 'pulado (já tem site)', 'avisos': [], 'modelo': None})
            continue
        if arquivo.exists() and not force:
            resultado.append({'slug': slug, 'status': 'já existe (use --force)', 'avisos': avisos,
                              'modelo': lead['site'].get('modelo')})
            continue
        if not dry_run:
            destino.mkdir(parents=True, exist_ok=True)
            cab = ('# Importado do pacote de hotsites. Sem foto de propósito: peça a original e a\n'
                   f'# autorização de imagem; coloque em app/static/img/demo/{slug}/ (capa.jpg, logo.jpg,\n'
                   '# produto-<nome>.jpg). Troque `site.modelo` se outro layout combinar mais.\n')
            arquivo.write_text(cab + yaml.safe_dump(lead, allow_unicode=True, sort_keys=False, width=100),
                               encoding='utf-8')
        resultado.append({'slug': slug, 'status': 'simulado' if dry_run else 'criado',
                          'avisos': avisos, 'modelo': lead['site'].get('modelo')})
    return resultado


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('json', help='expositores.json do pacote')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args(argv)
    for r in importar(args.json, args.dry_run, args.force):
        print(f"[{r['status']}] {r['slug']}" + (f"  modelo={r['modelo']}" if r['modelo'] else ''))
        for a in r['avisos']:
            print(f'    - {a}')


if __name__ == '__main__':
    main()
