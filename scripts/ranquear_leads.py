"""Em que ordem vale a pena trabalhar os bares.

O crédito de geração de imagem é finito e o tempo de rua também. Este script
responde uma pergunta só: **quais bares primeiro?**

O critério não é gosto. É o cruzamento de duas coisas que dá pra medir:

    movimento comprovado   quantas pessoas avaliaram (não quantas dizem gostar)
    satisfação             a nota

Um bar com 4,9 e 12 avaliações é uma família elogiando. Um com 4,5 e 2.757 é uma
rua inteira. O segundo tem mais gente passando pela porta, e é quem sente falta
de um site.

Dois ajustes por cima:

- quem **já tem site** vale menos: a conversa é de troca, não de estreia;
- quem **já tem foto** vale mais: a prévia pode ser montada hoje.

Como usar
---------
    python3 scripts/ranquear_leads.py --barao        # os 23 da rua desta semana
    python3 scripts/ranquear_leads.py --top 5        # só o topo
    python3 scripts/ranquear_leads.py --sem-foto     # quem precisa de imagem
    python3 scripts/ranquear_leads.py --slugs        # só os slugs, pra pipe

Só lê. Nunca escreve.
"""
import argparse
import glob
import os
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_LEADS = os.path.join(REPO, 'app', 'data', 'leads')
DIR_FOTOS = os.path.join(REPO, 'app', 'static', 'img', 'demo')

# Acima disso, mais avaliações não mudam a conclusão: o bar já é movimentado.
# Sem o teto, um bar de 4.000 avaliações esmagaria todo o resto da lista e a
# ordem viraria só "quem tem mais avaliação".
TETO_AVALIACOES = 1500

PESO_SEM_SITE = 1.5   # não tem site: é a venda inteira, não uma troca
PESO_COM_FOTO = 1.3   # dá pra montar a prévia hoje
PESO_COM_ZAP = 1.15   # dá pra mandar o link na hora


def _nota(valor):
    """'4,7' -> 4.7. Vírgula decimal é como o Google mostra e como gravamos."""
    try:
        return float(str(valor).replace(',', '.'))
    except (TypeError, ValueError):
        return 0.0


def _inteiro(valor):
    try:
        return int(str(valor).replace('.', '').strip())
    except (TypeError, ValueError):
        return 0


def carregar(apenas_barao=False, incluir_vitrine=False):
    linhas = []
    for caminho in sorted(glob.glob(os.path.join(DIR_LEADS, '*.yml'))):
        slug = os.path.basename(caminho)[:-4]
        bruto = open(caminho, encoding='utf-8').read()

        # Casa fechada não entra: gastar imagem e visita nela é perda dupla.
        if 'NÃO VISITAR' in bruto:
            continue
        d = yaml.safe_load(bruto) or {}
        if d.get('ativo') is False:
            continue
        # Bar-vitrine é material de demonstração, não prospecção.
        fonte = (d.get('demo') or {}).get('fonte') or ''
        if fonte == 'vitrine-da-campanha' and not incluir_vitrine:
            continue

        s = d.get('site') or {}
        regiao = f"{s.get('cidade_uf') or ''} {s.get('endereco') or ''}"
        if apenas_barao and 'Barão Geraldo' not in regiao:
            continue

        nota = _nota(s.get('nota_google'))
        avaliacoes = _inteiro(s.get('qtd_avaliacoes'))
        fotos = glob.glob(os.path.join(DIR_FOTOS, slug, '*.jpg'))
        tem_capa = any(os.path.basename(f) == 'capa.jpg' for f in fotos)
        tem_site = bool(s.get('site_url') or s.get('website'))
        tem_zap = bool(s.get('whatsapp'))

        pontos = (nota / 5) * (min(avaliacoes, TETO_AVALIACOES) / TETO_AVALIACOES)
        if not tem_site:
            pontos *= PESO_SEM_SITE
        if fotos:
            pontos *= PESO_COM_FOTO
        if tem_zap:
            pontos *= PESO_COM_ZAP

        linhas.append({
            'slug': slug,
            'nome': d.get('nome') or slug,
            'nota': nota,
            'avaliacoes': avaliacoes,
            'fotos': len(fotos),
            'tem_capa': tem_capa,
            'tem_site': tem_site,
            'tem_zap': tem_zap,
            'pontos': pontos,
        })

    linhas.sort(key=lambda x: -x['pontos'])
    return linhas


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--barao', action='store_true', help='só os bares de Barão Geraldo')
    p.add_argument('--top', type=int, metavar='N', help='só os N primeiros')
    p.add_argument('--sem-foto', action='store_true', help='só quem não tem capa')
    p.add_argument('--slugs', action='store_true', help='só os slugs, um por linha')
    p.add_argument('--vitrine', action='store_true', help='incluir bares-vitrine')
    a = p.parse_args()

    linhas = carregar(apenas_barao=a.barao, incluir_vitrine=a.vitrine)
    if a.sem_foto:
        linhas = [l for l in linhas if not l['tem_capa']]
    if a.top:
        linhas = linhas[:a.top]

    if a.slugs:
        for l in linhas:
            print(l['slug'])
        return 0

    print(f'\n{"#":>3} {"bar":26} {"nota":>4} {"aval":>6} {"fotos":>5} '
          f'{"site":>4} {"zap":>3}  pontos')
    print('-' * 68)
    for i, l in enumerate(linhas, 1):
        nota = f'{l["nota"]:.1f}'.replace('.', ',') if l['nota'] else '—'
        print(f'{i:>3} {l["nome"][:26]:26} {nota:>4} {l["avaliacoes"]:>6} '
              f'{l["fotos"]:>5} {"sim" if l["tem_site"] else "—":>4} '
              f'{"sim" if l["tem_zap"] else "—":>3}  {l["pontos"]:.3f}')

    sem_capa = [l for l in linhas if not l['tem_capa']]
    print(f'\n{len(linhas)} bares · {len(linhas) - len(sem_capa)} com capa · '
          f'{len(sem_capa)} sem')
    if sem_capa:
        print('Sem capa, na ordem de prioridade:')
        for l in sem_capa[:8]:
            print(f'  {l["slug"]:24} {l["avaliacoes"]:>6} avaliações')
    return 0


if __name__ == '__main__':
    sys.exit(main())
