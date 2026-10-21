"""Respostas do formulário de expositores -> um lead `.yml` por barraca.

O formulário (Google Forms) pergunta nome, barraca, dia de atendimento,
produtos, contatos, descrição, fotos e redes. Este script transforma cada
resposta em `app/data/leads/<slug>.yml`, o mesmo formato que o pipeline de
prévias já publica (`flask`/`/bootstrap-demo?action=demos`). Assim a escala dos
90+ artesãos usa o caminho que já funciona para os bares, sem criar outro.

    python -m app.scripts.importar_expositores respostas.csv --dry-run
    python -m app.scripts.importar_expositores respostas.xlsx

O que NÃO entra no arquivo
--------------------------
- E-mail e nome da pessoa: dado pessoal, e o `.yml` é versionado no git. O
  contato comercial que o site mostra é o WhatsApp da barraca.
- Fotos: o formulário traz links do Drive. O script só os lista, para o
  operador baixar para `app/static/img/demo/<slug>/` (capa.jpg, logo.jpg,
  produto-<nome>.jpg). Produto sem foto fica oculto na vitrine até ganhar uma.
"""
import argparse
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.utils.site_router import gerar_slug

DIR_LEADS = Path(__file__).resolve().parents[1] / 'data' / 'leads'

# Cada campo é achado pelo INÍCIO do cabeçalho normalizado: o Google Forms
# trunca cabeçalhos longos e o dono do formulário pode reescrever o final.
COLUNAS = {
    'barraca': 'nome da barraca',
    'expositor': 'nome do expositor',
    'dias': 'dia de atendimento',
    'produtos': 'produtos',
    'telefone': 'contato - telefone',
    'whatsapp': 'contato - whatsapp',
    'descricao': 'breve descritivo',
    'fotos': 'fotos',
    'instagram': 'instagram',
    'facebook': 'facebook',
}
MAX_PRODUTOS = 40


def _norm(texto):
    base = unicodedata.normalize('NFKD', str(texto or ''))
    return ''.join(c for c in base if not unicodedata.combining(c)).casefold().strip()


def _texto(valor):
    return re.sub(r'\s+', ' ', str(valor or '')).strip()


def mapear_colunas(cabecalho):
    """{campo: índice} casando o começo de cada cabeçalho. Campo ausente fica de fora."""
    normalizados = [_norm(c) for c in cabecalho]
    achados = {}
    for campo, prefixo in COLUNAS.items():
        for i, h in enumerate(normalizados):
            if h.startswith(prefixo):
                achados[campo] = i
                break
    return achados


def whatsapp_digitos(valor):
    """Só dígitos com DDI 55, ou None quando não dá pra confiar no número."""
    d = re.sub(r'\D', '', str(valor or ''))
    if d.startswith('55') and len(d) in (12, 13):
        return d
    if len(d) in (10, 11):
        return '55' + d
    return None


def telefone_exibicao(whatsapp):
    d = (whatsapp or '')[2:]
    if len(d) == 11:
        return f'({d[:2]}) {d[2:7]}-{d[7:]}'
    if len(d) == 10:
        return f'({d[:2]}) {d[2:6]}-{d[6:]}'
    return None


def url_instagram(valor):
    v = _texto(valor)
    if not v:
        return None
    if v.startswith(('http://', 'https://')):
        return v
    usuario = v.lstrip('@').strip('/ ')
    return f'https://www.instagram.com/{usuario}/' if re.fullmatch(r'[\w.]+', usuario) else None


def url_facebook(valor):
    v = _texto(valor)
    if not v:
        return None
    if v.startswith(('http://', 'https://')):
        return v
    return f'https://{v}' if 'facebook.com' in v.lower() else None


def horario_da_feira(dias):
    d = _norm(dias)
    sab, dom = 'sabado' in d, 'domingo' in d
    if sab and dom:
        return 'Sábados e domingos na Feira de Barão'
    if sab:
        return 'Sábados na Feira de Barão'
    if dom:
        return 'Domingos na Feira de Barão'
    return 'Na Feira de Barão'


def lista_de_produtos(valor):
    """'Geleia, Pimenta; Molho' -> nomes únicos, na ordem em que vieram."""
    vistos, saida = set(), []
    for bruto in re.split(r'[,;\n•]+', str(valor or '')):
        nome = _texto(bruto).strip('-– ')
        if len(nome) < 2 or _norm(nome) in vistos:
            continue
        vistos.add(_norm(nome))
        saida.append(nome[:1].upper() + nome[1:])
    return saida[:MAX_PRODUTOS]


def converter_linha(linha, cols, tipo='artesao'):
    """Uma resposta -> (slug, dict do lead, avisos). Devolve None sem nome de barraca."""
    def pega(campo):
        i = cols.get(campo)
        return linha[i] if i is not None and i < len(linha) else None

    nome = _texto(pega('barraca')) or _texto(pega('expositor'))
    if not nome:
        return None
    avisos = []
    slug = gerar_slug(nome)

    zap = whatsapp_digitos(pega('whatsapp')) or whatsapp_digitos(pega('telefone'))
    if not zap:
        avisos.append('sem WhatsApp válido (o botão de pedir não aparece)')

    site = {
        'whatsapp': zap,
        'telefone_exibicao': telefone_exibicao(zap),
        'tagline': _texto(pega('descricao'))[:300] or None,
        'instagram_url': url_instagram(pega('instagram')),
        'facebook_url': url_facebook(pega('facebook')),
        'horario': horario_da_feira(pega('dias')),
        'cidade_uf': 'Barão Geraldo, Campinas–SP',
        'kicker': 'FEIRA DE BARÃO · CAMPINAS–SP',
        'descritor': None,
        'vibe': 'artesanal' if tipo == 'artesao' else None,
    }
    site = {k: v for k, v in site.items() if v}

    produtos = [{'nome': n} for n in lista_de_produtos(pega('produtos'))]
    if not produtos:
        avisos.append('nenhum produto listado')

    lead = {'nome': nome, 'tipo_negocio': tipo, 'site': site}
    if produtos:
        lead['produtos'] = produtos
    lead['demo'] = {'fonte': 'formulario-expositores'}

    fotos = _texto(pega('fotos'))
    if fotos:
        avisos.append(f'fotos para baixar: {fotos}')
    else:
        avisos.append('sem fotos (a vitrine fica em "catálogo em montagem")')
    return slug, lead, avisos


def ler_planilha(caminho):
    """Linhas do CSV (exportado do Forms) ou do XLSX. A primeira é o cabeçalho."""
    caminho = str(caminho)
    if caminho.lower().endswith(('.xlsx', '.xlsm')):
        import openpyxl
        wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
        return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
    import csv
    with open(caminho, encoding='utf-8-sig', newline='') as f:
        return list(csv.reader(f))


def importar(caminho, tipo='artesao', dry_run=False, force=False, destino=None):
    """Gera os `.yml`. Devolve [{slug, arquivo, status, avisos}]."""
    import yaml
    destino = Path(destino or DIR_LEADS)
    linhas = ler_planilha(caminho)
    if not linhas:
        return []
    cols = mapear_colunas(linhas[0])
    if 'barraca' not in cols and 'expositor' not in cols:
        raise SystemExit('Não achei a coluna "Nome da Barraca" nem "Nome do Expositor" no cabeçalho.')

    resultado, usados = [], set()
    for linha in linhas[1:]:
        conv = converter_linha(linha, cols, tipo)
        if conv is None:
            continue
        slug, lead, avisos = conv
        base, n = slug, 2
        while slug in usados:                       # duas barracas com o mesmo nome
            slug, n = f'{base}-{n}', n + 1
        usados.add(slug)
        arquivo = destino / f'{slug}.yml'
        if arquivo.exists() and not force:
            resultado.append({'slug': slug, 'arquivo': str(arquivo), 'status': 'já existe (use --force)',
                              'avisos': avisos})
            continue
        if not dry_run:
            destino.mkdir(parents=True, exist_ok=True)
            cabecalho = ('# Importado do formulário de expositores. Fotos: coloque em\n'
                         f'# app/static/img/demo/{slug}/ (capa.jpg, logo.jpg, produto-<nome>.jpg).\n')
            arquivo.write_text(cabecalho + yaml.safe_dump(lead, allow_unicode=True, sort_keys=False),
                               encoding='utf-8')
        resultado.append({'slug': slug, 'arquivo': str(arquivo),
                          'status': 'simulado' if dry_run else 'criado', 'avisos': avisos})
    return resultado


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('planilha', help='CSV ou XLSX exportado do formulário')
    ap.add_argument('--tipo', choices=('artesao', 'bar'), default='artesao')
    ap.add_argument('--dry-run', action='store_true', help='mostra o que faria, sem gravar')
    ap.add_argument('--force', action='store_true', help='sobrescreve .yml existente')
    args = ap.parse_args(argv)
    for r in importar(args.planilha, args.tipo, args.dry_run, args.force):
        print(f"[{r['status']}] {r['slug']}")
        for a in r['avisos']:
            print(f'    - {a}')


if __name__ == '__main__':
    main()
