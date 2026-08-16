"""Em que pé está a presença digital de cada bar — e o que falta nela.

O que isto responde, por bar:

    tem avaliação no Google?  quantas?  que nota?
    tem foto?                 quantas?
    tem site?                 tem telefone?  tem horário?
    o Google sabe a faixa de preço?
    o perfil tem descrição?

A ausência é o produto. Bar sem foto, sem horário e sem site não perde venda por
ser ruim — perde porque quem procurou às 19h não achou nada e foi no vizinho. É
esse número que se diz na mesa, não uma opinião sobre o site dele.

Como usar
---------
    export GOOGLE_MAPS_API_KEY='...'

    python3 scripts/levantar_bares.py                 # levanta todos, não grava
    python3 scripts/levantar_bares.py --gravar        # grava nota/telefone/etc nos leads
    python3 scripts/levantar_bares.py --fotos 4       # baixa até 4 fotos por bar
    python3 scripts/levantar_bares.py tabuas confra   # só estes

Sem `--gravar` e sem `--fotos`, nada no repositório é tocado: roda, mostra o
levantamento e sai. É o modo de conferir antes de deixar escrever.

O relatório completo sai em `scripts/saida/levantamento.json`, com a resposta
crua da API por bar — pra conferir de onde veio cada número sem chamar de novo.
"""
import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import places_api  # noqa: E402  (precisa do sys.path acima)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_LEADS = os.path.join(REPO, 'app', 'data', 'leads')
DIR_FOTOS = os.path.join(REPO, 'app', 'static', 'img', 'demo')
DIR_SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saida')

# Quanto vale cada buraco na conversa de venda. Ordem = ordem de impacto:
# quem não tem foto perde antes de ser lido; quem não tem horário perde quem
# ia sair agora.
LACUNAS = (
    ('sem_foto',      'nenhuma foto no Google'),
    ('sem_horario',   'não diz que horas abre'),
    ('sem_site',      'não tem site'),
    ('poucas_avaliacoes', 'menos de 30 avaliações'),
    ('sem_avaliacao', 'nenhuma avaliação'),
    ('sem_telefone',  'sem telefone no perfil'),
    ('sem_descricao', 'perfil sem descrição'),
    ('sem_preco',     'Google não sabe a faixa de preço'),
)


def slugs_de_leads():
    """Bares ativos. Casa fechada (marcada no arquivo) fica de fora — gastar
    chamada em bar que não existe mais é queimar cota e sujar o relatório."""
    saida = []
    for arquivo in sorted(os.listdir(DIR_LEADS)):
        if not arquivo.endswith('.yml'):
            continue
        texto = open(os.path.join(DIR_LEADS, arquivo), encoding='utf-8').read()
        if 'NÃO VISITAR' in texto or re.search(r'^ativo:\s*false', texto, re.M):
            continue
        saida.append(arquivo[:-4])
    return saida


def nome_do_lead(slug):
    texto = open(os.path.join(DIR_LEADS, f'{slug}.yml'), encoding='utf-8').read()
    m = re.search(r'^nome:\s*"?([^"\n]+)"?', texto, re.M)
    return (m.group(1).strip() if m else slug.replace('-', ' '))


def _horario_legivel(bloco):
    """`regularOpeningHours.weekdayDescriptions` numa linha só.

    A API já devolve em pt-BR ("segunda-feira: 18:00 – 00:00"). Aqui só junta,
    porque o campo `horario` do lead é uma linha e o site imprime como veio.
    """
    if not bloco:
        return None
    linhas = bloco.get('weekdayDescriptions') or []
    return ' · '.join(l.strip() for l in linhas) or None


def avaliar(lugar):
    """Transforma a resposta da API no que interessa pra venda."""
    nota = lugar.get('rating')
    qtd = lugar.get('userRatingCount') or 0
    fotos = lugar.get('photos') or []
    horario = lugar.get('regularOpeningHours')

    estado = {
        'nome_google': (lugar.get('displayName') or {}).get('text'),
        'place_id': lugar.get('id'),
        'status': lugar.get('businessStatus'),
        'tipo': (lugar.get('primaryTypeDisplayName') or {}).get('text'),
        'nota': nota,
        'avaliacoes': qtd,
        'fotos': len(fotos),
        'site': lugar.get('websiteUri'),
        'telefone': lugar.get('nationalPhoneNumber'),
        'endereco': lugar.get('formattedAddress'),
        'horario': _horario_legivel(horario),
        'faixa_preco': lugar.get('priceLevel'),
        'descricao': (lugar.get('editorialSummary') or {}).get('text'),
        'depoimentos': len(lugar.get('reviews') or []),
    }

    estado['lacunas'] = [
        rotulo for chave, rotulo in LACUNAS
        if (chave == 'sem_foto' and not fotos)
        or (chave == 'sem_horario' and not estado['horario'])
        or (chave == 'sem_site' and not estado['site'])
        or (chave == 'sem_avaliacao' and qtd == 0)
        # "Poucas" só faz sentido pra quem tem alguma: senão o bar aparece nas
        # duas linhas e o relatório conta o mesmo problema duas vezes.
        or (chave == 'poucas_avaliacoes' and 0 < qtd < 30)
        or (chave == 'sem_telefone' and not estado['telefone'])
        or (chave == 'sem_descricao' and not estado['descricao'])
        or (chave == 'sem_preco' and not estado['faixa_preco'])
    ]
    return estado


def gravar_no_lead(slug, estado):
    """Escreve no YAML o que o bar não tinha. Nunca sobrescreve o que já existe.

    Campo já preenchido veio de alguém que olhou (ou de coleta anterior
    conferida); a API não tem autoridade pra apagar isso. Só entra o que está
    faltando.
    """
    caminho = os.path.join(DIR_LEADS, f'{slug}.yml')
    texto = open(caminho, encoding='utf-8').read()
    gravados = []

    campos = (
        ('nota_google', estado['nota'] and f'{estado["nota"]:.1f}'.replace('.', ',')),
        ('avaliacoes_google', estado['avaliacoes'] or None),
        ('telefone_exibicao', estado['telefone']),
        ('endereco', estado['endereco']),
        ('horario', estado['horario']),
    )
    for chave, valor in campos:
        if not valor:
            continue
        if re.search(rf'^\s+{chave}:', texto, re.M):
            continue  # já tem: respeita
        linha = f"  {chave}: '{valor}'"
        texto = re.sub(r'^(site:\n)', rf'\1{linha}\n', texto, count=1, flags=re.M)
        gravados.append(chave)

    if gravados:
        open(caminho, 'w', encoding='utf-8').write(texto)
    return gravados


def baixar_fotos(slug, lugar, quantas):
    """Fotos oficiais + o arquivo de créditos que a licença exige.

    A primeira vira `capa.jpg` (é o hero) e as demais entram como galeria, que é
    a convenção que `demos.fotos_do_bar()` já lê. Foto que já existe na pasta não
    é baixada de novo — foto do dono, tirada na visita, vale mais que a do Google
    e não pode ser atropelada por uma re-execução.
    """
    fotos = (lugar.get('photos') or [])[:quantas]
    if not fotos:
        return [], []

    pasta = os.path.join(DIR_FOTOS, slug)
    os.makedirs(pasta, exist_ok=True)
    baixadas, creditos = [], []

    for i, foto in enumerate(fotos):
        alvo = os.path.join(pasta, 'capa.jpg' if i == 0 else f'foto-{i}.jpg')
        atribuicoes = [a.get('displayName') for a in (foto.get('authorAttributions') or [])]
        creditos.append({'arquivo': os.path.basename(alvo),
                         'autor': ', '.join(a for a in atribuicoes if a) or 'Google',
                         'fonte': 'Google Places'})
        if os.path.exists(alvo):
            continue
        try:
            dados = places_api.baixar_foto(foto['name'])
        except Exception as e:  # noqa: BLE001 — uma foto falha, as outras seguem
            print(f'      foto {i}: {e}')
            continue
        with open(alvo, 'wb') as f:
            f.write(dados)
        baixadas.append(os.path.basename(alvo))

    if creditos:
        with open(os.path.join(pasta, 'creditos.json'), 'w', encoding='utf-8') as f:
            json.dump(creditos, f, ensure_ascii=False, indent=1)
    return baixadas, creditos


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('slugs', nargs='*', help='bares a levantar (padrão: todos)')
    p.add_argument('--gravar', action='store_true',
                   help='escreve nota/telefone/horário nos leads que não têm')
    p.add_argument('--fotos', type=int, default=0, metavar='N',
                   help='baixa até N fotos oficiais por bar')
    p.add_argument('--pausa', type=float, default=0.3, metavar='SEG',
                   help='intervalo entre bares (padrão 0.3)')
    args = p.parse_args()

    alvos = args.slugs or slugs_de_leads()
    print(f'{len(alvos)} bares · gravar={args.gravar} · fotos={args.fotos}\n')

    resultados, falhas = {}, []
    for n, slug in enumerate(alvos, 1):
        nome = nome_do_lead(slug)
        try:
            lugar = places_api.procurar(nome)
        except places_api.SemChave as e:
            print(f'\n{e}')
            return 2
        except places_api.ErroDaAPI as e:
            print(f'{n:3}. {slug:24} ERRO {e}')
            falhas.append(slug)
            continue

        if lugar is None:
            print(f'{n:3}. {slug:24} não achado no Google')
            falhas.append(slug)
            continue

        estado = avaliar(lugar)
        resultados[slug] = {'estado': estado, 'bruto': lugar}

        nota = f'{estado["nota"]:.1f}'.replace('.', ',') if estado['nota'] else '—'
        print(f'{n:3}. {slug:24} {nota:>4} ({estado["avaliacoes"]:>5}) '
              f'{estado["fotos"]:>2} fotos  {len(estado["lacunas"])} lacunas')

        if args.gravar:
            campos = gravar_no_lead(slug, estado)
            if campos:
                print(f'      gravado: {", ".join(campos)}')
        if args.fotos:
            baixadas, _ = baixar_fotos(slug, lugar, args.fotos)
            if baixadas:
                print(f'      fotos: {", ".join(baixadas)}')

        time.sleep(args.pausa)

    os.makedirs(DIR_SAIDA, exist_ok=True)
    caminho = os.path.join(DIR_SAIDA, 'levantamento.json')
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)

    # ---------------------------------------------------------------- resumo
    estados = [r['estado'] for r in resultados.values()]
    print(f'\n{"="*64}\n{len(estados)} levantados, {len(falhas)} sem resposta')
    if falhas:
        print('  sem resposta: ' + ', '.join(falhas))

    print('\nQuantos bares têm cada buraco:')
    for _, rotulo in LACUNAS:
        quantos = sum(1 for e in estados if rotulo in e['lacunas'])
        if quantos:
            barra = '█' * round(quantos / max(len(estados), 1) * 30)
            print(f'  {rotulo:34} {quantos:3} {barra}')

    piores = sorted(estados, key=lambda e: -len(e['lacunas']))[:10]
    print('\nOnde a conversa é mais fácil (mais buracos):')
    for e in piores:
        print(f'  {(e["nome_google"] or "?")[:30]:32} {len(e["lacunas"])} · '
              f'{", ".join(e["lacunas"][:3])}')

    com_nota = [e for e in estados if e['nota']]
    if com_nota:
        media = sum(e['nota'] for e in com_nota) / len(com_nota)
        print(f'\nNota média da rua: {media:.2f}'.replace('.', ','))
        print(f'Bares bem avaliados (4,5+) mas sem site: '
              f'{sum(1 for e in com_nota if e["nota"] >= 4.5 and not e["site"])}')

    print(f'\nRelatório: {caminho}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
